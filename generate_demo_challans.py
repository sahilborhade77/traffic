import cv2
import numpy as np
import os
from datetime import datetime, timedelta
from src.notification.echallan_pdf import EChallanPDFGenerator

def create_demo_data():
    """Generates a set of demo E-Challan PDFs for presentation."""
    print("Generating demo E-Challan data...")
    
    # Setup generator
    output_dir = 'output/demo_challans'
    gen = EChallanPDFGenerator(output_dir=output_dir)
    
    # Create output dir
    os.makedirs(output_dir, exist_ok=True)
    
    # Demo cases
    demo_cases = [
        {
            "id": 1001,
            "plate": "MH12-DE-4567",
            "owner": "Sahil Borhade",
            "type": "OVERSPEEDING",
            "location": "Mumbai-Pune Expressway, KM 45",
            "speed": "124 km/h",
            "fine": 2000,
            "color": (0, 0, 255) # Red for speeding
        },
        {
            "id": 1002,
            "plate": "MH14-AZ-8899",
            "owner": "Rajesh Kumar",
            "type": "RED_LIGHT_VIOLATION",
            "location": "Hinjewadi Phase 1 Circle",
            "speed": "22 km/h",
            "fine": 1000,
            "color": (255, 0, 0) # Blue for red light
        },
        {
            "id": 1003,
            "plate": "MH01-BB-0001",
            "owner": "Priya Sharma",
            "type": "WRONG_WAY_DRIVING",
            "location": "Bandra Worli Sea Link Entry",
            "speed": "45 km/h",
            "fine": 5000,
            "color": (0, 255, 0) # Green for wrong way
        },
        {
            "id": 1004,
            "plate": "MH12-XY-1234",
            "owner": "Amit Patel",
            "type": "TRIPLE_RIDING",
            "location": "FC Road, Pune",
            "speed": "30 km/h",
            "fine": 1500,
            "color": (255, 255, 0) # Yellow for triple riding
        }
    ]
    
    generated_files = []
    
    for case in demo_cases:
        # Create a "fake" evidence image with labels
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, f"VIOLATION: {case['type']}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, case['color'], 2)
        cv2.putText(img, f"PLATE: {case['plate']}", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(img, f"LOCATION: {case['location']}", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
        cv2.putText(img, f"SPEED: {case['speed']}", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
        
        # Add a simulated "bounding box"
        cv2.rectangle(img, (200, 250), (450, 400), case['color'], 3)
        
        img_path = os.path.join(output_dir, f"evidence_{case['id']}.jpg")
        cv2.imwrite(img_path, img)
        
        # Generate PDF
        pdf_path = gen.generate(
            violation_id=case['id'],
            plate_number=case['plate'],
            owner_name=case['owner'],
            owner_phone="+91-9988776655",
            violation_type=case['type'],
            violation_location=case['location'],
            violation_timestamp=datetime.now() - timedelta(hours=np.random.randint(1, 48)),
            camera_id=f"CAM-INTR-{np.random.randint(10, 99)}",
            fine_amount=float(case['fine']),
            evidence_image_path=img_path
        )
        generated_files.append(pdf_path)
        print(f"Generated: {pdf_path}")
        
    print(f"\nDone! All demo challans are in: {os.path.abspath(output_dir)}")
    return generated_files

if __name__ == "__main__":
    create_demo_data()
