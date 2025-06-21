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
from datetime import datetime, timedelta, timezone
import ee
import pandas as pd
from dotenv import load_dotenv
from db import get_last_processed_date, set_last_processed
from utils import get_description, zoi
from webhook_notifier import send_webhook_notification
from email_notifier import send_email_notification


load_dotenv()
CREDENTIALS_JSON = os.getenv("EARTHENGINE_CREDENTIALS")
save_folder = os.getenv("GDRIVE_FOLDER", "GEE_Soil_Moisture")

ee.Initialize()

today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=5)
START_DATE = yesterday.strftime("%Y-%m-%d")
END_DATE = today.strftime("%Y-%m-%d")

exported_data = []

# Load SMAP dataset
smap = (
    ee.ImageCollection("NASA/SMAP/SPL4SMGP/007")
    .filterBounds(zoi)
    .filterDate(START_DATE, END_DATE)
    .select("sm_surface")
)


# cls && .venv\Scripts\python.exe src/main.py
def main():
    """
    Main function to aggregate and print the array of start times from the SMAP dataset.

    This function retrieves the 'system:time_start' property from the SMAP dataset using the
    aggregate_array method, converts it to a Python list with getInfo(), and prints the resulting dates.

    Note:
        The export functionality (run_export) is currently commented out.
    """
    dates = smap.aggregate_array("system:time_start").getInfo()

    last = get_last_processed_date()

    # Convert timestamps to datetime objects
    image_dates = [datetime.fromtimestamp(ts / 1000, tz=timezone.utc) for ts in dates]

    # Filter images that are after the last processed date (or all if None)
    if last:
        new_dates = [dt for dt in image_dates if dt.date() > last]
    else:
        new_dates = image_dates

    # ✅ Example log
    if new_dates:
        updated_smap = (
            ee.ImageCollection("NASA/SMAP/SPL4SMGP/007")
            .filterBounds(zoi)
            .filterDate(new_dates[0], new_dates[-1])
            .select("sm_surface")
        )
        print(f"🆕 {len(new_dates)} new dates to process.")
        print("From:", new_dates[0], "→", new_dates[-1])
        print(f"🆕 Found {len(new_dates)} new dates to process.")

        ts = f"{new_dates[0]}_{new_dates[-1]}"
        run_export(updated_smap, ts)
    else:
        print("✅ No new dates to process.")


def extract_data(img):
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
        folder=save_folder,
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
        reducer=ee.Reducer.mean(),
        geometry=zoi,
        scale=10000,
        maxPixels=1e9,
    ).getInfo()

    vv = mean_dict.get("sm_surface", None)
    exported_data.append(
        {
            "date": date_str,
            "vv_dB": vv,
            "description": get_description(vv),
        }
    )


# Run export
def run_export(smap_to_use, times):
    """
    Processes and exports soil moisture images from the SMAP dataset within a specified date range.
    This function retrieves a list of images from the `smap_to_use` object, checks if any images are available,
    and iterates through each image to extract data using the `extract_data` function. If no images are found,
    a warning message is printed. If an error occurs while processing an image, an error message is displayed
    with the corresponding index and exception details.
    Raises:
        ee.EEException: If an error occurs during image processing.
    """

    # Run export
    images = smap_to_use.toList(smap_to_use.size())
    image_count = smap_to_use.size().getInfo()
    if image_count == 0:
        print("⚠️ No images found for the specified date range.")
    else:
        for i in range(image_count):
            try:
                image = ee.Image(images.get(i))
                extract_data(image)
            except ee.EEException as e:
                print(f"❌ Failed to process image at index {i}: {e}")

    bulk_notify_and_hook(times)


def bulk_notify_and_hook(times):
    """
    Processes and exports collected soil moisture data, then sends notifications.
    If `exported_data` is available, this function:
    - Converts the data to a pandas DataFrame.
    - Saves the DataFrame as a CSV file in the 'exports' directory, named with the current `START_DATE` and `END_DATE`.
    - Prints the path to the saved CSV file.
    - Sends a webhook notification with the list of dates in the exported data.
    - Sends an email notification with the CSV file attached.
    If no data is available, prints a warning message.
    Assumes the existence of the following global variables and functions:
    - `exported_data`: List of dictionaries containing soil moisture data.
    - `START_DATE`, `END_DATE`: Strings representing the date range of the data.
    - `send_webhook_notification(dates: exported_data)`: Function to send a webhook notification.
    - `send_email_notification (mode: str, file_path: str)`: Function to send an email notification.
    """
    if exported_data:
        df = pd.DataFrame(exported_data)
        os.makedirs("exports", exist_ok=True)
        combined_csv_path = f"exports/soil_moisture_{START_DATE}_{END_DATE}.csv"
        df.to_csv(combined_csv_path, index=False)
        print(f"💾 Combined CSV saved: {combined_csv_path}")

        # ✅ One-time notification
        send_webhook_notification(exported_data)
        send_email_notification(times, combined_csv_path)
        set_last_processed(exported_data)
    else:
        print("⚠️ No data to export or notify.")


main()
