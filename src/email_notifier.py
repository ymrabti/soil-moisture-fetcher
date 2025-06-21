"""
This module provides functionality to send email notifications with a SMAP soil moisture report,
including both plain text and HTML content, and optionally attaches a CSV report.
Environment Variables:
    SMTP_HOST (str): SMTP server hostname.
    SMTP_PORT (int): SMTP server port (default: 587).
    SMTP_USER (str): SMTP username.
    SMTP_PASS (str): SMTP password.
    EMAIL_FROM (str): Sender email address.
    EMAIL_TO (str): Recipient email address.
Functions:
    send_email_notification (date_str, csv_path):
        Sends an email notification for the specified date, with an optional CSV attachment.
            csv_path (str, optional): Path to the CSV file to attach. If None or file does not exist, no attachment is sent.
Author: Younes MRABTI
"""

import os
import smtplib

from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()

smtp_host = os.getenv("SMTP_HOST")
smtp_port = int(os.getenv("SMTP_PORT", "587"))
smtp_user = os.getenv("SMTP_USER")
smtp_pass = os.getenv("SMTP_PASS")
email_from = os.getenv("EMAIL_FROM")
email_to = os.getenv("EMAIL_TO")


def send_email_notification(date_str, csv_path):
    """
    Sends an email notification with a SMAP soil moisture report for the specified date.
    The email includes both plain text and HTML content,
    and optionally attaches a CSV report if a file path is provided.
    SMTP server configuration and email addresses are read from environment variables:
        - SMTP_HOST: SMTP server hostname
        - SMTP_PORT: SMTP server port (default: 587)
        - SMTP_USER: SMTP username
        - SMTP_PASS: SMTP password
        - EMAIL_FROM: Sender email address
        - EMAIL_TO: Recipient email address
    Args:
        date_str (str): The date string to include in the email subject and body.
        csv_path (str, optional): Path to the CSV file to attach.
        If None or file does not exist, no attachment is sent.
    Raises:
        smtplib.SMTPException: If sending the email fails.
    """
    today = datetime.now(timezone.utc).date()
    today_date = today.strftime("%Y-%m-%d %H:%M")
    subject = f"🛰️ {today_date} SMAP Soil Moisture Data - {date_str}"
    text_body = f"New SMAP soil moisture data for {date_str} is now available. See attached CSV."

    html_body = f"""
    <html>
      <body style="font-family: sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="background: white; padding: 20px; border-radius: 10px; max-width: 600px; margin: auto;">
          <h2 style="color: #2e6da4;">🌱 SMAP Soil Moisture Report</h2>
          <p>📅 <strong>Date:</strong> {date_str}</p>
          <p>A new SMAP soil moisture image has been exported and is available on Google Drive.</p>
          <p>The CSV report is attached.</p>
          <hr>
          <p style="font-size: 12px; color: #888;">This is an automated message from your soil moisture monitoring system.</p>
        </div>
      </body>
    </html>
    """

    msg = EmailMessage()
    msg["From"] = email_from
    msg["To"] = email_to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    # Attach CSV if it exists
    if csv_path and os.path.exists(csv_path):
        with open(csv_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(csv_path)}"',
            )
            msg.attach(part)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            print("📧 Email with CSV report sent.")
    except smtplib.SMTPException as e:
        print(f"❌ Email send failed: {e}")
