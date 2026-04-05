"""
Demo Video Processing Script.

Processes video files and adds overlays:
- Vehicle detection bounding boxes
- Vehicle count metrics
- Signal state indicators
- Traffic density heatmap
- Performance metrics (FPS, latency)
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from datetime import datetime
import time


class VideoOverlay:
    """Add overlays to video frames."""
    
    def __init__(self, frame_width: int, frame_height: int):
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # Color definitions
        self.COLORS = {
            'car': (0, 255, 0),          # Green
            'truck': (255, 0, 0),         # Blue
            'motorcycle': (0, 255, 255),  # Yellow
            'bus': (255, 255, 0),         # Cyan
            'green_signal': (0, 255, 0),  # Green
            'yellow_signal': (0, 255, 255),  # Yellow
            'red_signal': (0, 0, 255),    # Red
            'text': (255, 255, 255),      # White
            'background': (0, 0, 0),      # Black
        }
    
    def draw_detection_boxes(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """Draw bounding boxes for detected vehicles."""
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            class_name = detection.get('class', 'unknown')
            confidence = detection.get('confidence', 0.0)
            
            color = self.COLORS.get(class_name, (0, 255, 255))
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label with background
            label = f"{class_name} {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 4),
                         (x1 + label_size[0], y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def draw_vehicle_count(self, frame: np.ndarray, count: int, lane: str) -> np.ndarray:
        """Draw vehicle count overlay."""
        text = f"{lane} Lane: {count} vehicles"
        
        # Position depends on lane
        positions = {
            'North': (20, 40),
            'South': (20, self.frame_height - 20),
            'East': (self.frame_width - 250, 40),
            'West': (20, 40),
        }
        
        x, y = positions.get(lane, (20, 40))
        
        # Draw semi-transparent background
        overlay = frame.copy()
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        cv2.rectangle(overlay, (x - 5, y - 30),
                     (x + text_size[0] + 5, y + 5),
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Draw text
        cv2.putText(frame, text, (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        return frame
    
    def draw_signal_state(self, frame: np.ndarray, signals: Dict[str, str]) -> np.ndarray:
        """Draw traffic signal state indicators."""
        # Define signal positions (intersection points)
        signal_positions = {
            'North': (self.frame_width // 2, 50),
            'South': (self.frame_width // 2, self.frame_height - 50),
            'East': (self.frame_width - 50, self.frame_height // 2),
            'West': (50, self.frame_height // 2),
        }
        
        for lane, state in signals.items():
            pos = signal_positions.get(lane, (0, 0))
            color = self.COLORS.get(f'{state}_signal', (128, 128, 128))
            
            # Draw circle for signal indicator
            cv2.circle(frame, pos, 25, color, -1)
            
            # Draw state text
            cv2.putText(frame, state.upper()[0], (pos[0] - 8, pos[1] + 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
        
        return frame
    
    def draw_density_heatmap(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """Draw traffic density heatmap overlay."""
        # Create density map
        density_map = np.zeros((self.frame_height, self.frame_width), dtype=np.float32)
        
        # Accumulate density from detections
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            
            # Draw Gaussian blob at detection center
            cv2.circle(density_map, (cx, cy), 50, 1.0, -1)
        
        # Normalize density map
        if density_map.max() > 0:
            density_map = (density_map / density_map.max() * 255).astype(np.uint8)
        
        # Apply colormap
        heatmap = cv2.applyColorMap(density_map, cv2.COLORMAP_JET)
        
        # Blend with original frame
        frame = cv2.addWeighted(frame, 0.7, heatmap, 0.3, 0)
        
        return frame
    
    def draw_performance_metrics(self, frame: np.ndarray, fps: float,
                                latency_ms: float, detections: int) -> np.ndarray:
        """Draw performance metrics overlay."""
        y_offset = 80
        metrics = [
            f"FPS: {fps:.1f}",
            f"Latency: {latency_ms:.1f}ms",
            f"Detections: {detections}",
        ]
        
        # Draw semi-transparent background
        overlay = frame.copy()
        text_height = 25 * len(metrics)
        cv2.rectangle(overlay, (10, 10), (250, 20 + text_height),
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Draw metrics
        for i, metric in enumerate(metrics):
            y = 30 + i * 25
            cv2.putText(frame, metric, (20, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        
        return frame
    
    def draw_timestamp(self, frame: np.ndarray, timestamp: Optional[str] = None) -> np.ndarray:
        """Draw timestamp on frame."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cv2.putText(frame, timestamp, (self.frame_width - 280, self.frame_height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame
    
    def draw_legend(self, frame: np.ndarray) -> np.ndarray:
        """Draw legend for overlays."""
        legend_items = [
            ("Green Box: Car", (0, 255, 0)),
            ("Blue Box: Truck", (255, 0, 0)),
            ("Yellow Box: Motorcycle", (0, 255, 255)),
        ]
        
        y_start = 100
        x_start = self.frame_width - 250
        
        for i, (label, color) in enumerate(legend_items):
            y = y_start + i * 25
            
            # Draw color box
            cv2.rectangle(frame, (x_start, y - 10), (x_start + 15, y + 5), color, -1)
            
            # Draw label
            cv2.putText(frame, label, (x_start + 20, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame


def generate_sample_detections(frame_count: int) -> List[List[Dict]]:
    """Generate sample detection data for demo."""
    detections_list = []
    
    for frame_idx in range(frame_count):
        frame_detections = []
        
        # Simulate 8-15 vehicles per frame
        num_vehicles = np.random.randint(8, 15)
        
        for v_idx in range(num_vehicles):
            # Random position
            x1 = np.random.randint(50, 1200)
            y1 = np.random.randint(50, 650)
            x2 = x1 + np.random.randint(40, 120)
            y2 = y1 + np.random.randint(40, 120)
            
            vehicle_types = ['car', 'truck', 'motorcycle', 'bus']
            
            detection = {
                'bbox': (x1, y1, x2, y2),
                'class': np.random.choice(vehicle_types),
                'confidence': np.random.uniform(0.85, 0.99),
            }
            frame_detections.append(detection)
        
        detections_list.append(frame_detections)
    
    return detections_list


def generate_sample_signals(frame_count: int) -> List[Dict[str, str]]:
    """Generate sample signal state data."""
    signals_list = []
    cycle_length = 120  # 120 frames per cycle
    
    for frame_idx in range(frame_count):
        cycle_pos = frame_idx % cycle_length
        
        # Simulate 4-way traffic signal
        if cycle_pos < 40:
            signals = {'North': 'green', 'South': 'red',
                      'East': 'red', 'West': 'green'}
        elif cycle_pos < 45:
            signals = {'North': 'yellow', 'South': 'red',
                      'East': 'green', 'West': 'yellow'}
        elif cycle_pos < 85:
            signals = {'North': 'red', 'South': 'green',
                      'East': 'green', 'West': 'red'}
        else:
            signals = {'North': 'red', 'South': 'yellow',
                      'East': 'yellow', 'West': 'red'}
        
        signals_list.append(signals)
    
    return signals_list


class DemoVideoGenerator:
    """Generate demo video with overlays."""
    
    def __init__(self, output_path: str, width: int = 1280, height: int = 720, fps: int = 30):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.width = width
        self.height = height
        self.fps = fps
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(str(self.output_path), fourcc, fps, (width, height))
        
        self.overlay = VideoOverlay(width, height)
    
    def create_blank_frame(self) -> np.ndarray:
        """Create blank frame with gradient background."""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Add gradient background
        for i in range(self.height):
            frame[i, :] = [20, 20, 40]
        
        # Draw road markings
        cv2.line(frame, (self.width // 2, 0), (self.width // 2, self.height),
                (100, 100, 100), 2)
        cv2.line(frame, (0, self.height // 2), (self.width, self.height // 2),
                (100, 100, 100), 2)
        
        return frame
    
    def add_frame_with_overlays(self, detections: List[Dict], signals: Dict[str, str],
                               lane: str = "North", fps: float = 30.0,
                               latency_ms: float = 50.0):
        """Add frame with all overlays."""
        frame = self.create_blank_frame()
        
        # Add overlays
        frame = self.overlay.draw_detection_boxes(frame, detections)
        frame = self.overlay.draw_vehicle_count(frame, len(detections), lane)
        frame = self.overlay.draw_signal_state(frame, signals)
        frame = self.overlay.draw_density_heatmap(frame, detections)
        frame = self.overlay.draw_performance_metrics(frame, fps, latency_ms, len(detections))
        frame = self.overlay.draw_timestamp(frame)
        frame = self.overlay.draw_legend(frame)
        
        # Write frame
        self.writer.write(frame)
    
    def generate_demo(self, num_frames: int = 300):
        """Generate complete demo video."""
        print(f"Generating demo video: {self.output_path}")
        print(f"Resolution: {self.width}x{self.height} @ {self.fps} FPS")
        print(f"Duration: {num_frames / self.fps:.1f} seconds\n")
        
        # Generate sample data
        detections_list = generate_sample_detections(num_frames)
        signals_list = generate_sample_signals(num_frames)
        
        # Simulate performance metrics
        start_time = time.time()
        
        for frame_idx in range(num_frames):
            # Simulate FPS variation
            fps = 28 + 4 * np.sin(frame_idx * 0.02)
            
            # Simulate latency variation
            latency_ms = 50 + 20 * np.sin(frame_idx * 0.01)
            
            self.add_frame_with_overlays(
                detections_list[frame_idx],
                signals_list[frame_idx],
                lane="North",
                fps=fps,
                latency_ms=latency_ms
            )
            
            # Progress indicator
            if (frame_idx + 1) % 30 == 0:
                print(f"✓ Processed {frame_idx + 1}/{num_frames} frames")
        
        elapsed = time.time() - start_time
        print(f"\n✅ Demo video generated successfully!")
        print(f"📹 Video saved to: {self.output_path}")
        print(f"⏱️  Processing time: {elapsed:.2f} seconds")
        print(f"🎬 Play with: ffplay '{self.output_path}' or any video player")
    
    def close(self):
        """Close video writer."""
        if self.writer is not None:
            self.writer.release()


def main():
    """Generate demo video."""
    output_file = "demos/traffic_demo.mp4"
    
    generator = DemoVideoGenerator(output_file, width=1280, height=720, fps=30)
    
    try:
        generator.generate_demo(num_frames=300)  # 10 seconds at 30 FPS
    finally:
        generator.close()


if __name__ == "__main__":
    main()
