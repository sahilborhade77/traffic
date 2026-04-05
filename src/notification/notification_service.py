import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Handles alerts via SMS, Email, and WhatsApp for traffic violations.
    Connects to external gateways (e.g. Twilio, SendGrid, etc.).
    """
    def __init__(self, sms_config: Dict[str, Any], email_config: Dict[str, Any]):
        """
        Initialize the notification engine with gateway configs.
        """
        self.sms_config = sms_config
        self.email_config = email_config
        logger.info("Notification Service initialized.")

    def send_violation_alert(self, violation_id: int, owner_phone: str, owner_email: str, violation_type: str, fine_amount: float):
        """
        Send a multi-channel alert to the vehicle owner.
        """
        message = (
            f"TRAFFIC ALERT: A {violation_type} was recorded for your vehicle. "
            f"Violation ID: {violation_id}. Fine amount: ₹{fine_amount}. "
            "Please visit the e-challan portal to pay."
        )
        
        # Simulate SMS
        logger.info(f"SMS SENT to {owner_phone}: {message[:50]}...")
        
        # Simulate Email
        logger.info(f"EMAIL SENT to {owner_email}: Subject: E-Challan Issued - {violation_id}")
        
        return True

    def send_broadcast(self, title: str, message: str):
        """Send a general alert to all dashboard subscribers."""
        logger.info(f"Broadcasting Alert: {title} - {message}")
