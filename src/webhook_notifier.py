"""
This module provides functionality to send webhook notifications when new data becomes available.
Functions:
    send_webhook_notification(date_str):
        Sends a POST request to a webhook URL specified by the WEBHOOK_URL environment variable,
        notifying about the availability of new data for a given date.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

webhook_url = os.getenv("WEBHOOK_URL")


def send_webhook_notification(date_str):
    """
    Sends a webhook notification to a specified URL with information about new data availability.

    Args:
        date_str (str): The date string representing when new data is available.

    Environment Variables:
        WEBHOOK_URL: The URL to which the webhook notification will be sent.

    Behavior:
        - If the WEBHOOK_URL environment variable is not set,
        the function returns without sending a notification.
        - Sends a POST request with a JSON payload containing the status and date.
        - Prints the status code of the response if successful.
        - Prints an error message if the request fails.

    Exceptions:
        Handles requests.RequestException and prints an
        error message if the webhook fails to send.
    """

    if not webhook_url:
        return
    try:
        payload = {"status": "new_data_available", "date": date_str}
        r = requests.post(webhook_url, json=payload, timeout=2000)
        print(f"📡 Webhook sent: {r.status_code}")
    except requests.RequestException as e:
        print(f"❌ Webhook failed: {e}")
