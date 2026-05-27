#!/usr/bin/env python3
"""
End-to-end demo runner for the Smart AI Traffic Intelligence System.

Flow:
video input -> vehicle detection -> tracking -> plate detection/OCR ->
evidence image -> database violation -> E-Challan PDF
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import cv2

from src.database.violation_db import ViolationDatabase
from src.detection.plate_detector import PlateDetector
from src.detection.vehicle_detector import VehicleDetector
from src.evidence.evidence_manager import EvidenceManager
from src.notification.echallan_pdf import EChallanPDFGenerator
from src.ocr.plate_ocr import IndianPlateOCR
from src.tracking.deepsort_tracker import DeepSORTTracker
from src.violations.violation_types import ViolationType, get_fine_amount


LOGGER = logging.getLogger("full_demo")


def read_demo_frame(video_path: str, frame_index: int):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video input: {video_path}")

    frame = None
    for _ in range(max(1, frame_index + 1)):
        ok, frame = cap.read()
        if not ok:
            break
    cap.release()

    if frame is None:
        raise RuntimeError(f"Could not read a frame from {video_path}")
    return frame


def choose_vehicle(frame, detections):
    if detections:
        bbox_ltwh, confidence, class_id = max(detections, key=lambda item: item[1])
        x, y, w, h = bbox_ltwh
        return {
            "bbox_ltwh": [int(x), int(y), int(w), int(h)],
            "confidence": float(confidence),
            "class_id": int(class_id),
            "source": "yolo"
        }

    height, width = frame.shape[:2]
    fallback_w = int(width * 0.5)
    fallback_h = int(height * 0.45)
    x = int(width * 0.25)
    y = int(height * 0.35)
    return {
        "bbox_ltwh": [x, y, fallback_w, fallback_h],
        "confidence": 0.0,
        "class_id": 2,
        "source": "fallback_region"
    }


def crop_from_ltwh(frame, bbox):
    x, y, w, h = bbox
    frame_h, frame_w = frame.shape[:2]
    x1 = max(0, int(x))
    y1 = max(0, int(y))
    x2 = min(frame_w, x1 + max(1, int(w)))
    y2 = min(frame_h, y1 + max(1, int(h)))
    return frame[y1:y2, x1:x2], [x1, y1, x2 - x1, y2 - y1]


def run_demo(args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = read_demo_frame(args.video, args.frame_index)

    detector = VehicleDetector(model_path=args.vehicle_model)
    tracker = DeepSORTTracker(max_age=15, n_init=1)
    plate_detector = PlateDetector(model_path=args.plate_model)
    ocr = IndianPlateOCR(use_gpu=False)
    db = ViolationDatabase(db_url=args.db_url)
    evidence = EvidenceManager(output_dir=str(output_dir / "evidence"))
    pdf = EChallanPDFGenerator(output_dir=str(output_dir / "challans"))

    detections = detector.detect(frame)
    tracks = tracker.update(detections, frame) if detections else {}
    vehicle = choose_vehicle(frame, detections)
    vehicle_crop, bbox_ltwh = crop_from_ltwh(frame, vehicle["bbox_ltwh"])

    plate_number = args.demo_plate
    plate_source = "demo_fallback"
    plate_detection = plate_detector.detect(vehicle_crop)
    ocr_confidence = 0.0

    if plate_detection:
        px, py, pw, ph = plate_detection.bbox
        plate_crop = vehicle_crop[py:py + ph, px:px + pw]
        ocr_result = ocr.read_plate(plate_crop)
        if ocr_result and ocr_result.is_valid:
            plate_number = ocr_result.cleaned_text
            plate_source = "ocr"
            ocr_confidence = float(ocr_result.confidence)

    metadata = {
        "track_id": next(iter(tracks.keys()), 1),
        "vehicle_detection_source": vehicle["source"],
        "vehicle_detection_confidence": vehicle["confidence"],
        "tracker_active_tracks": len(tracks),
        "plate_source": plate_source,
        "plate_detector_confidence": plate_detection.confidence if plate_detection else 0.0,
        "ocr_confidence": ocr_confidence,
        "demo_note": "RTO/owner lookup and notification delivery are simulated for academic demo scope."
    }

    violation_type = ViolationType.OVERSPEEDING
    fine_amount = get_fine_amount(violation_type)
    evidence_paths = evidence.capture_violation_evidence(
        frame=frame,
        bbox=bbox_ltwh,
        violation_type=violation_type.name,
        metadata={**metadata, "plate_number": plate_number}
    )

    violation_id = db.create_violation(
        plate_number=plate_number,
        violation_type=violation_type.name,
        camera_id=args.camera_id,
        timestamp=datetime.now(),
        fine_amount=fine_amount,
        metadata=metadata,
        image_path=evidence_paths["image_path"],
        location=args.location
    )

    challan_path = pdf.generate(
        violation_id=violation_id,
        plate_number=plate_number,
        owner_name=args.owner_name,
        owner_phone=args.owner_phone,
        violation_type=violation_type.value,
        violation_location=args.location,
        violation_timestamp=datetime.now(),
        camera_id=args.camera_id,
        fine_amount=fine_amount,
        evidence_image_path=evidence_paths["image_path"]
    )

    annotated = frame.copy()
    x, y, w, h = bbox_ltwh
    cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 180, 255), 2)
    cv2.putText(
        annotated,
        f"{violation_type.value}: {plate_number}",
        (x, max(25, y - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 180, 255),
        2
    )
    annotated_path = output_dir / "full_demo_annotated.jpg"
    cv2.imwrite(str(annotated_path), annotated)

    result = {
        "status": "ok",
        "video": args.video,
        "violation_id": violation_id,
        "plate_number": plate_number,
        "plate_source": plate_source,
        "evidence_image": evidence_paths["image_path"],
        "metadata": evidence_paths["metadata_path"],
        "challan_pdf": challan_path,
        "annotated_image": str(annotated_path),
        "database": args.db_url
    }

    result_path = output_dir / "full_demo_result.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


def parse_args():
    parser = argparse.ArgumentParser(description="Run a complete traffic enforcement demo.")
    parser.add_argument("--video", default="data/traffic_sample.mp4")
    parser.add_argument("--frame-index", type=int, default=30)
    parser.add_argument("--output-dir", default="output/full_demo")
    parser.add_argument("--db-url", default="sqlite:///traffic.db")
    parser.add_argument("--vehicle-model", default="yolov8n.pt")
    parser.add_argument("--plate-model", default="models/yolov8n_plate.pt")
    parser.add_argument("--demo-plate", default="MH12AB1234")
    parser.add_argument("--camera-id", default="CAM_DEMO_01")
    parser.add_argument("--location", default="Demo Junction")
    parser.add_argument("--owner-name", default="Demo Vehicle Owner")
    parser.add_argument("--owner-phone", default="+91-0000000000")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    run_demo(parse_args())
