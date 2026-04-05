"""
Traffic Intelligence System (TIS) — Full Integration Pipeline v2.0
====================================================================
Integrates all 10 features with strict 4GB VRAM management:
  1. Wrong-Way Detection
  2. Triple Riding Detection
  3. Phone-While-Driving Detection
  4. Congestion Heatmap
  5. E-Challan PDF
  6. FastAPI Dashboard (runs separately via src/api/main_api.py)
  7. Repeat Offender Engine
  8. Night Vision Enhancement
  9. Alembic Migrations (run via: alembic upgrade head)
  10. Multi-Camera (run via: python scripts/run_multi_camera.py)
"""

import cv2
import numpy as np
from datetime import datetime
import logging
import asyncio
from pathlib import Path

# ── VRAM-Aware Shared Model Manager ──
from src.utils.model_manager import model_manager

# ── Detection ──
from src.detection.plate_detector import PlateDetector

# ── Tracking ──
from src.tracking.deepsort_tracker import DeepSORTTracker

# ── OCR ──
from src.ocr.plate_ocr import IndianPlateOCR

# ── Violation Detectors ──
from src.violations.red_light_detector import RedLightViolationDetector, SignalState
from src.violations.speed_enforcer import AverageSpeedEnforcer, VehiclePassage, SpeedZone
from src.violations.wrong_way_detector import WrongWayDetector
from src.violations.triple_riding_detector import TripleRidingDetector
from src.violations.phone_detector import PhoneDetector
from src.violations.repeat_offender import RepeatOffenderEngine

# ── Analytics ──
from src.analytics.heatmap_generator import HeatmapGenerator

# ── Evidence & Notifications ──
from src.evidence.evidence_manager import EvidenceManager
from src.notification.echallan_pdf import EChallanPDFGenerator
from src.notification.notification_service import NotificationService

# ── Database ──
from src.database.violation_db import ViolationDatabase

# ── Utilities ──
from src.utils.config import load_config
from src.utils.night_vision import NightVisionEnhancer

logging.basicConfig(level=logging.INFO, format='%(asctime)s — %(name)s — %(levelname)s — %(message)s')
logger = logging.getLogger("TIS_v2")

# Fine map from violations.yaml (base amounts)
BASE_FINES = {
    'RED_LIGHT': 1000,
    'OVERSPEEDING_AVERAGE': 2000,
    'WRONG_WAY': 5000,
    'TRIPLE_RIDING': 1000,
    'PHONE_WHILE_DRIVING': 1000,
}


class TrafficEnforcementSystem:
    """
    Unified TIS Pipeline v2.0
    All 10 features active. Shared ModelManager keeps VRAM ≤ 4GB.
    """

    def __init__(self, config_path: str = 'config/cameras.yaml'):
        logger.info("=" * 60)
        logger.info("  Traffic Intelligence System v2.0  Starting...")
        logger.info("=" * 60)

        self.config = load_config(config_path)

        # ── Step 1: Initialize shared GPU model (ONE YOLO + EasyOCR in VRAM) ──
        yolo_path = self.config.get('models', {}).get('vehicle_detection', 'yolov8n.pt')
        model_manager.initialize(yolo_model_path=yolo_path, use_gpu=True)

        # ── Step 2: Plate detector + OCR (shares EasyOCR from model_manager) ──
        self.plate_detector = PlateDetector(
            model_path=self.config.get('models', {}).get('plate_detection', 'yolov8n.pt')
        )
        self.plate_ocr = IndianPlateOCR(use_gpu=True)

        # Lazy ANPR cache:  track_id → plate_number  (avoid re-reading every frame)
        self._anpr_cache: dict = {}

        # ── Step 3: Tracking ──
        self.tracker = DeepSORTTracker()

        # ── Step 4: Database ──
        db_url = self.config.get('database', {}).get('url', 'sqlite:///traffic.db')
        self.db = ViolationDatabase(db_url=db_url)

        # ── Step 5: Violation Detectors ──
        rl_cfg = self.config.get('red_light', {
            'stop_line_y': 450,
            'violation_threshold': 30,
            'roi_polygon': np.array([[100, 400], [600, 400], [600, 650], [100, 650]])
        })
        self.red_light_det = RedLightViolationDetector(config=rl_cfg)

        self.wrong_way_det = WrongWayDetector(
            expected_flow_angle=float(self.config.get('traffic_flow_angle', 90.0)),
            tolerance_degrees=45.0
        )
        self.triple_riding_det = TripleRidingDetector()
        self.phone_det = PhoneDetector(conf_threshold=0.45, cooldown_frames=60)

        # Speed zones from config
        speed_zones = {
            zid: SpeedZone(**zcfg)
            for zid, zcfg in self.config.get('speed_zones', {}).items()
        }
        self.speed_enforcer = AverageSpeedEnforcer(speed_zones=speed_zones, db_manager=self.db)

        # Repeat offender engine
        self.repeat_offender = RepeatOffenderEngine(db_manager=self.db)

        # ── Step 6: Analytics ──
        frame_h = self.config.get('frame_height', 720)
        frame_w = self.config.get('frame_width', 1280)
        self.heatmap = HeatmapGenerator(frame_shape=(frame_h, frame_w))

        # ── Step 7: Evidence & PDF ──
        evidence_dir = self.config.get('evidence', {}).get('output_dir', 'output/evidence')
        self.evidence_mgr = EvidenceManager(output_dir=evidence_dir)
        self.pdf_gen = EChallanPDFGenerator(output_dir='output/challans')
        self.notif_svc = NotificationService(
            sms_config=self.config.get('notifications', {}).get('sms', {}),
            email_config=self.config.get('notifications', {}).get('email', {})
        )

        # ── Step 8: Night Vision ──
        self.night_vision = NightVisionEnhancer(clip_limit=2.5, gamma=1.2)

        # State
        self.prev_signal_state = None
        self.frame_count = 0

        logger.info("TIS v2.0 fully initialized. All 10 features active.")
        model_manager._log_vram()

    # ──────────────────────────────────────────────────────────
    # MAIN FRAME PROCESSOR
    # ──────────────────────────────────────────────────────────

    def process_frame(self, frame: np.ndarray, camera_id: str) -> np.ndarray:
        """
        Single-frame TIS pipeline — all 10 features run here.
        """
        self.frame_count += 1

        # ── Feature 8: Night Vision (auto-activates in low light) ──
        frame, enhanced = self.night_vision.smart_enhance(frame, threshold=80.0)

        # ── Module 1: Detect (shared YOLO — vehicles + persons + phones) ──
        # Vehicles: COCO classes 2=car, 3=motorcycle, 5=bus, 7=truck
        vehicle_results = model_manager.detect(frame, conf=0.3, classes=[2, 3, 5, 7])

        # Convert to DeepSORT format: ([x,y,w,h], conf, class_id)
        raw_detections = []
        for box in vehicle_results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            raw_detections.append(([x1, y1, x2 - x1, y2 - y1], conf, cls))

        # ── Module 2: Track ──
        tracks = self.tracker.update(raw_detections, frame)

        # ── Feature 4: Update Heatmap ──
        self.heatmap.update(tracks)

        # ── Traffic Signal Detection ──
        signal_roi = self.config.get('cameras', {}).get(camera_id, {}).get('signal_roi', [50, 50, 100, 200])
        signal_state = self.red_light_det.detect_signal_state(frame, signal_roi)

        # ── Per-track Violation Checks ──
        for track_id, track in tracks.items():
            bbox_xyxy = track.bbox  # (x1, y1, x2, y2)
            cls_id = track.class_id
            is_bike = (cls_id == 3)  # COCO motorcycle

            # ── Feature 1: Wrong-Way ──
            ww = self.wrong_way_det.check(track)
            if ww:
                self._handle_violation(frame, track, 'WRONG_WAY', camera_id,
                                        {'angle': ww.measured_angle})

            # ── Red Light Violation ──
            rl_vehicle = self._to_rl_detection(track)
            rl = self.red_light_det.check_violation(rl_vehicle, signal_state, self.prev_signal_state)
            if rl:
                self._handle_violation(frame, track, 'RED_LIGHT', camera_id,
                                        {'signal': signal_state.value,
                                         'crossing_px': rl.crossing_distance})

            # ── Feature 2: Triple Riding (bikes only) ──
            if is_bike and self.frame_count % 10 == 0:
                tr = self.triple_riding_det.check(frame, track_id, bbox_xyxy, model_manager)
                if tr:
                    self._handle_violation(frame, track, 'TRIPLE_RIDING', camera_id,
                                            {'person_count': tr.person_count})

            # ── Feature 3: Phone Detection (every 30 frames per track) ──
            if self.frame_count % 30 == 0:
                ph = self.phone_det.check(frame, track_id, bbox_xyxy, model_manager, self.frame_count)
                if ph:
                    self._handle_violation(frame, track, 'PHONE_WHILE_DRIVING', camera_id,
                                            {'confidence': ph.confidence})

            # ── ANPR — Lazy (once per track ID) ──
            if track_id not in self._anpr_cache and self.frame_count % 15 == 0:
                plate = self._read_plate(frame, bbox_xyxy)
                if plate:
                    self._anpr_cache[track_id] = plate

                    # ── Module 5: Speed Enforcement ──
                    passages_dir = self.config.get('evidence', {}).get('passages_dir', 'output/evidence/passages')
                    passage_img = self._save_crop(frame, bbox_xyxy, passages_dir, plate)
                    passage = VehiclePassage(
                        plate_number=plate,
                        camera_id=camera_id,
                        timestamp=datetime.now(),
                        image_path=passage_img
                    )
                    self.speed_enforcer.record_vehicle_passage(passage)

        # ── Visualization ──
        # Every 60 frames render heatmap overlay briefly
        if self.frame_count % 60 < 10:
            annotated = self.heatmap.render(frame, alpha=0.4)
        else:
            annotated = self.red_light_det.draw_visualization(
                frame, [self._to_rl_detection(t) for t in tracks.values()], signal_state
            )

        # Night vision indicator
        if enhanced:
            cv2.putText(annotated, "🌙 NIGHT VISION ON", (10, annotated.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        self.prev_signal_state = signal_state
        return annotated

    # ──────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────

    def _to_rl_detection(self, track):
        """Map VehicleTrack → RedLightViolationDetector.VehicleDetection."""
        from src.violations.red_light_detector import VehicleDetection as RLD
        x1, y1, x2, y2 = track.bbox
        w, h = int(x2 - x1), int(y2 - y1)
        cx, cy = track.get_centroid()
        return RLD(
            track_id=track.track_id,
            bbox=(int(x1), int(y1), w, h),
            centroid=(int(cx), int(cy)),
            vehicle_class="unknown",
            confidence=track.confidence
        )

    def _read_plate(self, frame, bbox_xyxy) -> str:
        """Run ANPR on vehicle crop. Returns cleaned plate string or empty."""
        x1, y1, x2, y2 = map(int, bbox_xyxy)
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return ""
        crop = frame[y1:y2, x1:x2]
        plate_det = self.plate_detector.detect(crop)
        if not plate_det:
            return ""
        px, py, pw, ph = map(int, plate_det.bbox)
        plate_crop = crop[py:py + ph, px:px + pw]
        result = self.plate_ocr.read_plate(plate_crop)
        return result.cleaned_text if (result and result.is_valid) else ""

    def _handle_violation(self, frame, track, vtype: str, camera_id: str, meta: dict):
        """Unified violation handler — Evidence → DB → Repeat Check → PDF → Notify."""
        plate = self._anpr_cache.get(track.track_id, "UNKNOWN")

        # 1. Capture evidence
        ev = self.evidence_mgr.capture_violation_evidence(
            frame=frame, bbox=track.bbox, violation_type=vtype,
            metadata={'track_id': track.track_id, **meta}
        )

        # 2. Repeat offender fine calculation
        base_fine = BASE_FINES.get(vtype, 500)
        fine_calc = self.repeat_offender.calculate_fine(
            plate_number=plate,
            base_fine=base_fine,
            violation_timestamp=datetime.now()
        )

        # 3. Commit to DB
        vid = self.db.create_violation(
            plate_number=plate,
            violation_type=vtype,
            camera_id=camera_id,
            timestamp=datetime.now(),
            fine_amount=fine_calc['final_fine'],
            metadata={**meta, **fine_calc},
            image_path=ev['image_path']
        )

        logger.warning(
            f"VIOLATION [{vtype}] Track={track.track_id} Plate={plate} "
            f"Fine=₹{fine_calc['final_fine']} ({fine_calc['reason']}) ID={vid}"
        )

        if vid and plate != "UNKNOWN":
            # 4. Generate PDF E-Challan
            owner = self.db.get_vehicle_owner(plate) or {}
            pdf_path = self.pdf_gen.generate(
                violation_id=vid,
                plate_number=plate,
                owner_name=owner.get('name', 'Unknown'),
                owner_phone=owner.get('phone', 'N/A'),
                violation_type=vtype.replace('_', ' ').title(),
                violation_location=self.config.get('cameras', {}).get(camera_id, {}).get('location', camera_id),
                violation_timestamp=datetime.now(),
                camera_id=camera_id,
                fine_amount=fine_calc['final_fine'],
                evidence_image_path=ev['image_path']
            )
            logger.info(f"E-Challan PDF: {pdf_path}")

            # 5. Send notification
            self.notif_svc.send_violation_alert(
                violation_id=vid,
                owner_phone=owner.get('phone', ''),
                owner_email=owner.get('email', ''),
                violation_type=vtype.replace('_', ' ').title(),
                fine_amount=fine_calc['final_fine']
            )

    def _save_crop(self, frame, bbox_xyxy, output_dir: str, plate: str) -> str:
        """Save vehicle passage crop image for speed tracking."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        x1, y1, x2, y2 = map(int, bbox_xyxy)
        h, w = frame.shape[:2]
        crop = frame[max(0,y1):min(h,y2), max(0,x1):min(w,x2)]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = str(Path(output_dir) / f"passage_{plate}_{ts}.jpg")
        cv2.imwrite(path, crop)
        return path

    # ──────────────────────────────────────────────────────────
    # ENTRYPOINTS
    # ──────────────────────────────────────────────────────────

    def run(self, video_source: str, camera_id: str):
        """Single-camera blocking loop."""
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            logger.error(f"Cannot open source: {video_source}")
            return

        logger.info(f"Processing Camera {camera_id} → {video_source}")
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                processed = self.process_frame(frame, camera_id)
                cv2.imshow(f"TIS v2.0 — {camera_id}", processed)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            model_manager.free_cache()
            logger.info("TIS Stopped. GPU cache cleared.")

    async def run_async(self, video_source: str, camera_id: str):
        """Async-compatible frame processor for MultiCameraManager."""
        loop = asyncio.get_event_loop()
        cap = cv2.VideoCapture(video_source)
        try:
            while cap.isOpened():
                ret, frame = await loop.run_in_executor(None, cap.read)
                if not ret:
                    break
                processed = self.process_frame(frame, camera_id)
                cv2.imshow(f"TIS — {camera_id}", processed)
                await asyncio.sleep(0.001)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()


if __name__ == "__main__":
    tis = TrafficEnforcementSystem(config_path='config/cameras.yaml')

    # Single camera (change to RTSP URL for live feed):
    # tis.run(video_source='data/test.mp4', camera_id='CAM_001')

    # Multi-camera (run separately):
    # python scripts/run_multi_camera.py
