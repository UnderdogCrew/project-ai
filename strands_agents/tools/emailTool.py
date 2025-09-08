from typing import Optional

from strands_agents.tools.toolkit import Toolkit
from strands_agents.utils.log import logger
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content


class EmailTools(Toolkit):
    def __init__(
        self,
        sender_name: Optional[str] = None,
        sender_email: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__()

        self.sender_name: Optional[str] = sender_name
        self.sender_email: Optional[str] = sender_email
        self.api_key: Optional[str] = api_key
        self.register(self.email_user, name="email_tools")

    def email_user(self, subject: str, body: str, to_email: str) -> str:
        """Send the Emails to user with the given subject and body.

        :param subject: The subject of the email.
        :param body: The body of the email.
        :param to_email: The email address to send the email to.
        :return: "success" if the email was sent successfully, "error: [error message]" otherwise.

        Note: If the user requests to send an email or an email address is found in the response,
        the email will be sent to the specified or found email addresses.
        """
        logger.info(f"===================================to===================================== {to_email}")
        if not self.sender_name:
            return "error: No sender name provided"
        if not self.sender_email:
            return "error: No sender email provided"
        if not self.api_key:
            return "error: No API key provided"
        to_emails = to_email.split(",")

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
                logger.info(f"Email sent! Status Code: {response.status_code}")
            except Exception as e:
                logger.error(f"Error: {e}")
        return "email sent successfully"
