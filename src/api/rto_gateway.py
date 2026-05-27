import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class RTOGateway:
    """
    Mock RTO (Regional Transport Office) API Gateway.
    Fetches vehicle owner details based on license plate number.
    Live VAHAN/NIC access is outside the academic project scope.
    """
    
    def __init__(self):
        self.mode = "mock"
        # Mock database of vehicle owners
        self._mock_db = {
            "MH12-DE-4567": {
                "owner_name": "Sahil Borhade",
                "phone": "+91-9988776655",
                "email": "sahil@example.com",
                "address": "Pune, Maharashtra",
                "vehicle_model": "Maruti Swift",
                "insurance_valid_until": "2026-12-31"
            },
            "MH14-AZ-8899": {
                "owner_name": "Rajesh Kumar",
                "phone": "+91-9876543210",
                "email": "rajesh@example.com",
                "address": "Pimpri-Chinchwad, Maharashtra",
                "vehicle_model": "Honda City",
                "insurance_valid_until": "2025-06-15"
            },
            "MH01-BB-0001": {
                "owner_name": "Priya Sharma",
                "phone": "+91-9000112233",
                "email": "priya@example.com",
                "address": "Mumbai, Maharashtra",
                "vehicle_model": "Mercedes C-Class",
                "insurance_valid_until": "2027-01-20"
            }
        }

    def fetch_owner_details(self, plate_number: str) -> Optional[Dict]:
        """
        Fetch details from the mock RTO database.
        """
        logger.info(f"RTO Lookup for plate: {plate_number}")
        
        # In a real system, this would be an API call to Vahan/NIC
        details = self._mock_db.get(plate_number)
        
        if details:
            return {**details, "lookup_mode": self.mode}
            
        # Return generic data if plate not in mock DB (simulating a fallback)
        return {
            "owner_name": "Unknown Owner",
            "phone": "+91-0000000000",
            "email": "unknown@rto.gov.in",
            "address": "Address not found in records",
            "vehicle_model": "Unknown",
            "insurance_valid_until": "Unknown",
            "lookup_mode": self.mode
        }
