import logging
import sys
import os

# Add src to path if needed
sys.path.append(os.getcwd())

from src.database.violation_db import ViolationDatabase, Vehicle
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DB_Setup")

def setup_database():
    """
    Physically initialize your database tables and seed test data.
    """
    logger.info("Initializing Traffic Intelligence System (TIS) Database...")
    
    # Use config from environmental variables or default to local sqlite
    db_url = os.getenv('DATABASE_URL', 'sqlite:///traffic.db')
    
    try:
        # 1. Connect and Create Tables
        db = ViolationDatabase(db_url=db_url)
        logger.info(f"Database tables checked/created at {db_url}")
        
        # 2. Seed Test Vehicles (RTO Registry)
        logger.info("Seeding initial test vehicles...")
        test_vehicles = [
            Vehicle(
                plate_number="MH12AB1234",
                owner_name="Sahil Borhade",
                owner_phone="+919876543210",
                owner_email="sahil.b@example.com",
                vehicle_type="car",
                registration_date=datetime(2022, 5, 15)
            ),
            Vehicle(
                plate_number="KA01HH9999",
                owner_name="Rahul Kumar",
                owner_phone="+918888888888",
                owner_email="rahul.k@example.com",
                vehicle_type="bike",
                registration_date=datetime(2023, 1, 10)
            )
        ]
        
        # Add to session
        for vehicle in test_vehicles:
            existing = db.session.query(Vehicle).filter(Vehicle.plate_number == vehicle.plate_number).first()
            if not existing:
                db.session.add(vehicle)
                logger.info(f"Seeded vehicle: {vehicle.plate_number}")
        
        db.session.commit()
        logger.info("Database Setup Successfully Completed!")
        
    except Exception as e:
        logger.error(f"FATAL: Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_database()
