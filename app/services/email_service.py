import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app.core.config import settings
from typing import Optional

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        if not settings.SENDGRID_API_KEY:
            logger.warning("SendGrid API key not configured")
            self.client = None
        else:
            self.client = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    
    async def send_contact_form_to_admin(
        self, 
        name: str, 
        email: str, 
        company: str, 
        message: str
    ) -> bool:
        """
        Send contact form details to admin via SendGrid
        
        Args:
            name: Name of the person who submitted the form
            email: Email of the person who submitted the form  
            company: Company of the person who submitted the form
            message: Message from the contact form
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.client:
            logger.error("SendGrid client not initialized. Check SENDGRID_API_KEY configuration.")
            return False
            
        if not settings.SENDGRID_FROM_EMAIL:
            logger.error("SENDGRID_FROM_EMAIL not configured")
            return False
            
        if not settings.ADMIN_EMAIL:
            logger.error("ADMIN_EMAIL not configured")
            return False
        
        try:
            # Create the email content
            subject = f"New Contact Form Submission from {name}"
            
            html_content = f"""
            <html>
            <body>
                <h2>New Contact Form Submission</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Company:</strong> {company}</p>
                <p><strong>Message:</strong></p>
                <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #007cba;">
                    {message}
                </div>
                <br>
                <p><small>This email was sent from the Underdog AI contact form.</small></p>
            </body>
            </html>
            """
            
            plain_text_content = f"""
            New Contact Form Submission
            
            Name: {name}
            Email: {email}
            Company: {company}
            
            Message:
            {message}
            
            This email was sent from the Underdog AI contact form.
            """
            
            # Create the email
            from_email = Email(settings.SENDGRID_FROM_EMAIL)
            to_email = To(settings.ADMIN_EMAIL)
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=plain_text_content,
                html_content=html_content
            )
            
            # Send the email
            response = self.client.send(mail)
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Contact form email sent successfully to admin. Status: {response.status_code}")
                return True
            else:
                logger.error(f"Failed to send contact form email. Status: {response.status_code}, Body: {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending contact form email: {str(e)}")
            return False
    
    async def send_general_admin_email(
        self, 
        subject: str, 
        content: str, 
        from_name: Optional[str] = None
    ) -> bool:
        """
        Send a general email to admin
        
        Args:
            subject: Email subject
            content: Email content (HTML or plain text)
            from_name: Optional sender name
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.client:
            logger.error("SendGrid client not initialized. Check SENDGRID_API_KEY configuration.")
            return False
            
        if not settings.SENDGRID_FROM_EMAIL or not settings.ADMIN_EMAIL:
            logger.error("Email configuration missing")
            return False
        
        try:
            from_email = Email(settings.SENDGRID_FROM_EMAIL, from_name)
            to_email = To(settings.ADMIN_EMAIL)
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=content
            )
            
            response = self.client.send(mail)
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Admin email sent successfully. Status: {response.status_code}")
                return True
            else:
                logger.error(f"Failed to send admin email. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending admin email: {str(e)}")
            return False

# Create a singleton instance
email_service = EmailService() 