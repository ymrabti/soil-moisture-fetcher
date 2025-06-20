import os
import ee
import requests
import smtplib
import pandas as pd
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
load_dotenv()

CREDENTIALS_JSON = os.getenv("EARTHENGINE_CREDENTIALS")

ee.Initialize()

# Zone of Interest
zoi = ee.Geometry.Polygon(
    [
        [
            [-6.913337630230819, 33.96372761379892],
            [-6.837643297965064, 34.041713419311066],
            [-6.715267025694914, 34.17661240168678],
            [-6.519459846919034, 34.12961911179728],
            [-6.595909944361779, 33.90255010085002],
            [-6.910131849580654, 33.82562201398678],
            [-6.913337630230819, 33.96372761379892],
        ]
    ]
)

today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=5)

START_DATE = yesterday.strftime("%Y-%m-%d")
END_DATE = today.strftime("%Y-%m-%d")

print(f"📅 Fetching data from {START_DATE} to {END_DATE}")


# Load SMAP dataset
smap = (
    ee.ImageCollection("NASA/SMAP/SPL4SMGP/007")
    .filterDate(START_DATE, END_DATE)
    .select("sm_surface")
)

"""
Function
"""
def export_and_notify(image):
    date_str = image.date().format("YYYY-MM-dd").getInfo()
    filename = f"smap_soil_moisture_{date_str}"

    task = ee.batch.Export.image.toDrive(
        image=image.clip(zoi),
        description=filename,
        folder=os.getenv("GDRIVE_FOLDER", "GEE_Soil_Moisture"),
        fileNamePrefix=filename,
        scale=10000,
        region=zoi,
        maxPixels=1e13,
        fileFormat="GeoTIFF",
    )
    task.start()
    print(f"🛰️ Export started for {date_str}")

    # 1. Extract soil moisture mean for your ZOI on this image
    mean_dict = image.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=zoi, scale=10000, maxPixels=1e9
    ).getInfo()

    # 2. Create a simple DataFrame
    df = pd.DataFrame(
        [{"date": date_str, "soil_moisture_mean": mean_dict.get("sm_surface", None)}]
    )

    # 3. Save CSV file locally
    csv_path = f"soil_moisture_{date_str}.csv"
    df.to_csv(csv_path, index=False)
    print(f"💾 CSV saved: {csv_path}")
    send_webhook_notification(date_str)
    # send_email_notification(date_str, csv_path)


def send_webhook_notification(date_str):
    url = os.getenv("WEBHOOK_URL")
    if not url:
        return
    try:
        payload = {"status": "new_data_available", "date": date_str}
        r = requests.post(url, json=payload, timeout=2000)
        print(f"📡 Webhook sent: {r.status_code}")
    except Exception as e:
        print(f"❌ Webhook failed: {e}")


def send_email_notification(date_str, csv_path=None):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    email_from = os.getenv("EMAIL_FROM")
    email_to = os.getenv("EMAIL_TO")

    subject = f"🛰️ SMAP Soil Moisture Data - {date_str}"
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
    except Exception as e:
        print(f"❌ Email send failed: {e}")


dates = smap.aggregate_array("system:time_start").getInfo()
if dates:

    for ts in dates[:5]:
        print(datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y-%m-%d"))
else:
    print("⚠️ No images found.")
# Run export
images = smap.toList(smap.size())
image_count = smap.size().getInfo()
if image_count == 0:
    print("⚠️ No images found for the specified date range.")
else:
    for i in range(image_count):
        try:
            image = ee.Image(images.get(i))
            export_and_notify(image)
        except Exception as e:
            print(f"❌ Failed to process image at index {i}: {e}")
