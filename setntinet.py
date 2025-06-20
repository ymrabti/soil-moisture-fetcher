"""
Main entry point for the Soil Moisture Fetcher.

This script automates the process of fetching daily NASA SMAP soil moisture data
for a specified Zone of Interest (ZOI) using Google Earth Engine (GEE). It computes
the mean soil moisture for the ZOI, exports clipped GeoTIFF images to Google Drive,
saves daily statistics as CSV files, and sends notifications via webhook and/or email.

Steps performed:
1. Loads environment variables and credentials.
2. Initializes the Google Earth Engine API.
3. Defines the ZOI polygon.
4. Fetches SMAP soil moisture images for the specified date range.
5. For each image:
   - Exports the clipped GeoTIFF to Google Drive.
   - Computes and saves the mean soil moisture as a CSV file.
   - Sends a notification with the CSV report via webhook and/or email.

Configuration is managed via a `.env` file.

Author: Younes Mrabti
"""

import os
import smtplib

from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate
from email.mime.base import MIMEBase
from email import encoders
import geemap.foliumap as geemap
import ee
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_JSON = os.getenv("EARTHENGINE_CREDENTIALS")

ee.Initialize()

# Zone of Interest
zoi = ee.Geometry.Polygon(
    [
        [
            [-2.3481773965156094, 35.10994069768071],
            [-2.3456620930114127, 35.1057921166766],
            [-2.3395766814241767, 35.10280500753562],
            [-2.331259952255124, 35.10466366608924],
            [-2.327568135891795, 35.11004026111742],
            [-2.326026498289366, 35.1151510164202],
            [-2.3265944700380317, 35.120560103022925],
            [-2.337020808557469, 35.12357974361997],
            [-2.3424976789862626, 35.12304882591104],
            [-2.3440393165879527, 35.11992961448671],
            [-2.344485580152309, 35.11820404187584],
            [-2.343674191940522, 35.115781541852286],
            [-2.3447289966161122, 35.113292596948455],
            [-2.3481773965156094, 35.10994069768071],
        ]
    ]
)

today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=15)

START_DATE = yesterday.strftime("%Y-%m-%d")
END_DATE = today.strftime("%Y-%m-%d")

print(f"📅 Fetching data from {START_DATE} to {END_DATE}")

exported_data = []

# Load SMAP dataset
smap = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(zoi)
    .filterDate(START_DATE, END_DATE)
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    .select("VV")
)


def export_and_notify(img):
    """
    Exports a given Earth Engine image to Google Drive,
    computes the mean soil moisture for a specified zone of interest (ZOI),
    saves the result as a local CSV file, and sends a webhook notification.
    Args:
        img (ee.Image): The Earth Engine image to export and analyze.
    Side Effects:
        - Starts an Earth Engine export task to Google Drive for the clipped image.
        - Prints status messages to the console.
        - Computes the mean soil moisture value ("sm_surface") for
        the ZOI and saves it as a CSV file locally.
        - Sends a webhook notification with the export date.
    Environment Variables:
        GDRIVE_FOLDER (str, optional): The Google Drive
        folder to export the image to. Defaults to "GEE_Soil_Moisture".
    Notes:
        - Requires the global variable `zoi` (zone of interest) to be defined.
        - Assumes the presence of the `send_webhook_notification` function.
        - Optionally, an email notification can be sent by uncommenting the relevant line.
    """
    date_str = img.date().format("YYYY-MM-dd").getInfo()
    filename = f"smap_soil_moisture_{date_str}"

    task = ee.batch.Export.image.toDrive(
        image=img.clip(zoi),
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
    mean_dict = img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=zoi, scale=10000, maxPixels=1e9
    ).getInfo()

    exported_data.append(
        {"date": date_str, "soil_moisture_mean": mean_dict.get("sm_surface", None)}
    )


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
    url = os.getenv("WEBHOOK_URL")
    if not url:
        return
    try:
        payload = {"status": "new_data_available", "date": date_str}
        r = requests.post(url, json=payload, timeout=2000)
        print(f"📡 Webhook sent: {r.status_code}")
    except requests.RequestException as e:
        print(f"❌ Webhook failed: {e}")


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
    except smtplib.SMTPException as e:
        print(f"❌ Email send failed: {e}")


def extract_vv_mean(img):
    stats = img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=zoi, scale=10, maxPixels=1e9
    )
    return ee.Feature(
        None, {"date": img.date().format("YYYY-MM-dd"), "vv": stats.get("VV")}
    )


features = smap.map(extract_vv_mean).filter(ee.Filter.notNull(["vv"]))
results = features.getInfo()["features"]
df = pd.DataFrame(
    [{"date": f["properties"]["date"], "vv_dB": f["properties"]["vv"]} for f in results]
)

df["date"] = pd.to_datetime(df["date"])
print(df)

# 2️⃣ Generate a colored map of the median VV over your ZOI

# Compute median image (reduce noise)
vv_median = smap.median().clip(zoi)
export_filename = f"Sentinel1_VV_{datetime.now().strftime('%Y%m%d_%H%M')}"
task = ee.batch.Export.image.toDrive(
    image=vv_median,
    description=export_filename,
    folder="GEE_Exports",  # Name of your Google Drive folder
    fileNamePrefix=export_filename,
    region=zoi,
    scale=10,  # 10m native resolution
    crs="EPSG:4326",
    maxPixels=1e9,
    fileFormat="GeoTIFF",
)

task.start()
# Visualization parameters for VV (dB)
vis_params = {
    "min": -25,
    "max": -5,
    "palette": ["0000FF", "00FFFF", "00FF00", "FFFF00", "FF0000"],  # Blue to Red
}

# Create interactive map with geemap
Map = geemap.Map(center=[34.01, -6.8], zoom=12)
# Add VV median layer with color ramp
Map.addLayer(vv_median, vis_params, "Sentinel-1 VV Median (dB)")
# Add ZOI outline
Map.addLayer(zoi, {"color": "white"}, "ZOI")
# Add colorbar
Map.add_colorbar(
    vis_params={"min": -25, "max": 0, "palette": ["#000000", "#888888", "#FFFFFF"]},
    label="VV (dB)",
)
# Display the map
Map
# cls && .venv\Scripts\python.exe setntinet.py

dates = smap.aggregate_array("system:time_start").getInfo()
if dates:
    first = datetime.fromtimestamp(dates[0] / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")
    last = datetime.fromtimestamp(dates[-1] / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")
    print(f"{first} → {last}")
else:
    print("⚠️ No images found.")
# Run export
images = smap.toList(smap.size())
image_count = smap.size().getInfo()

# if image_count == 0:
#     print("⚠️ No images found for the specified date range.")
# else:
#     for i in range(image_count):
#         try:
#             image = ee.Image(images.get(i))
#             export_and_notify(image)
#         except ee.EEException as e:
#             print(f"❌ Failed to process image at index {i}: {e}")

# if exported_data:
#     df = pd.DataFrame(exported_data)
#     os.makedirs("exports", exist_ok=True)
#     combined_csv_path = f"exports/soil_moisture_{START_DATE}_{END_DATE}.csv"
#     df.to_csv(combined_csv_path, index=False)
#     print(f"💾 Combined CSV saved: {combined_csv_path}")

#     # ✅ One-time notification
#     send_webhook_notification([d["date"] for d in exported_data])
#     send_email_notification("batch", combined_csv_path)
# else:
#     print("⚠️ No data to export or notify.")
