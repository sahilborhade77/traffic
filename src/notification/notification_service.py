import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Handles alerts via SMS, Email, and WhatsApp for traffic violations.
    Academic demo mode logs notifications instead of sending real SMS/email.
    """
    def __init__(self, sms_config: Dict[str, Any], email_config: Dict[str, Any]):
        """
        Initialize the notification engine with gateway configs.
        """
        self.sms_config = sms_config
        self.email_config = email_config
        self.mode = "mock"
        logger.info("Notification Service initialized in MOCK mode.")

    def send_violation_alert(self, violation_id: int, owner_phone: str, owner_email: str, violation_type: str, fine_amount: float):
        """
        Send a multi-channel alert to the vehicle owner.
        """
        message = (
            f"TRAFFIC ALERT: A {violation_type} was recorded for your vehicle. "
            f"Violation ID: {violation_id}. Fine amount: ₹{fine_amount}. "
            "Please visit the e-challan portal to pay."
        )
        
        # Mock SMS
        logger.info(f"[MOCK SMS] To {owner_phone}: {message[:50]}...")
        
        # Mock Email
        logger.info(f"[MOCK EMAIL] To {owner_email}: Subject: E-Challan Issued - {violation_id}")
        
        return {"delivered": True, "mode": self.mode, "channels": ["sms", "email"]}

    def send_broadcast(self, title: str, message: str):
        """Send a general alert to all dashboard subscribers."""
        logger.info(f"Broadcasting Alert: {title} - {message}")
