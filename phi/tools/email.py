from typing import Optional

from phi.tools import Toolkit
from phi.utils.log import logger
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content


class EmailTools(Toolkit):
    def __init__(
        self,
        sender_name: Optional[str] = None,
        sender_email: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(name="email_tools")
        self.sender_name: Optional[str] = sender_name
        self.sender_email: Optional[str] = sender_email
        self.api_key: Optional[str] = api_key
        self.register(self.email_user)

    def email_user(self, subject: str, body: str, to: str) -> str:
        """Emails the user with the given subject and body.

        :param subject: The subject of the email.
        :param body: The body of the email.
        :return: "success" if the email was sent successfully, "error: [error message]" otherwise.
        """
        try:
            import smtplib
            from email.message import EmailMessage
        except ImportError:
            logger.error("`smtplib` not installed")
            raise
        print(f"===================================to===================================== {to}")
        if not self.sender_name:
            return "error: No sender name provided"
        if not self.sender_email:
            return "error: No sender email provided"
        if not self.api_key:
            return "error: No API key provided"
        to_emails = to.split(",")
        # Create a SendGrid client
        sg = sendgrid.SendGridAPIClient(api_key=self.api_key)

        for _email in to_emails:
            # Define the email parameters
            from_email = Email(self.sender_email)  # Replace with your sender email
            # to_email = To(self.receiver_email)    # Replace with your recipient email
            to_email = _email #to    # Replace with your recipient email
            subject = subject
            content = Content("text/plain", body)

            # Create the Mail object
            mail = Mail(from_email, to_email, subject, content)

            logger.info(f"Sending Email to {_email}")
            # Send the email
            try:
                response = sg.send(mail)
                print(f"Email sent! Status Code: {response.status_code}")
            except Exception as e:
                print(f"Error: {e}")
        return "email sent successfully"
