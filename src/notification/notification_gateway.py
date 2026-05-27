import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class NotificationGateway:
    """
    Handles sending e-challans via SMS and Email.
    In a real-world scenario, this integrates with Twilio (SMS) and SendGrid (Email).
    """
    
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock
        logger.info(f"NotificationGateway initialized (Mock Mode: {use_mock})")

    def send_sms(self, phone_number: str, message: str) -> bool:
        """
        Sends an SMS alert to the vehicle owner.
        """
        if self.use_mock:
            logger.info(f"[MOCK SMS] To: {phone_number} | Msg: {message}")
            return True
        
        # Real Twilio Integration Example:
        # from twilio.rest import Client
        # client = Client(ACCOUNT_SID, AUTH_TOKEN)
        # client.messages.create(body=message, from_=TWILIO_PHONE, to=phone_number)
        return False

    def send_email(self, email_address: str, subject: str, body_html: str, attachment_path: str = None) -> bool:
        """
        Sends an Email with the e-challan PDF as an attachment.
        """
        if self.use_mock:
            logger.info(f"[MOCK EMAIL] To: {email_address} | Sub: {subject} | Attachment: {attachment_path}")
            return True

        # Real SendGrid Integration Example:
        # from sendgrid import SendGridAPIClient
        # from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
        # message = Mail(from_email=SENDER, to_emails=email_address, subject=subject, html_content=body_html)
        # if attachment_path:
        #     with open(attachment_path, 'rb') as f:
        #         data = f.read()
        #     encoded = base64.b64encode(data).decode()
        #     attachment = Attachment(FileContent(encoded), FileName(os.path.basename(attachment_path)), ...)
        #     message.add_attachment(attachment)
        # sg = SendGridAPIClient(API_KEY)
        # sg.send(message)
        return False

    def notify_violation(self, owner_info: dict, violation_data: dict, pdf_path: str):
        """
        High-level method to send both SMS and Email for a detected violation.
        """
        phone = owner_info.get('phone', 'Unknown')
        email = owner_info.get('email', 'Unknown')
        plate = violation_data.get('plate_number', 'Unknown')
        v_type = violation_data.get('violation_type', 'Violation').replace('_', ' ')
        
        # 1. Send SMS
        sms_msg = f"Traffic Violation Alert! Vehicle {plate} was caught for {v_type}. A fine of Rs. {violation_data['fine']} has been issued. View details: https://echallan.gov.in"
        self.send_sms(phone, sms_msg)
        
        # 2. Send Email
        email_sub = f"E-Challan Notice: {plate} ({v_type})"
        email_body = f"<h2>Traffic Violation Notice</h2><p>Dear {owner_info['name']}, your vehicle <b>{plate}</b> was recorded for <b>{v_type}</b>. Please find the official e-challan attached.</p>"
        self.send_email(email, email_sub, email_body, pdf_path)
        
        logger.info(f"Notifications sent for violation {violation_data.get('id')}")

# Example usage
if __name__ == "__main__":
    gateway = NotificationGateway(use_mock=True)
    
    owner = {"name": "Sahil Borhade", "phone": "+91-9988776655", "email": "sahil@example.com"}
    violation = {"id": 1001, "plate_number": "MH12-DE-4567", "violation_type": "OVERSPEEDING", "fine": 2000.0}
    pdf = "output/demo_challans/sample.pdf"
    
    gateway.notify_violation(owner, violation, pdf)
