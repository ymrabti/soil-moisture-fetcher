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
import time
import logging
from datetime import datetime, timedelta, timezone
import ee
import pandas as pd

# from db import get_last_processed_date
from db import create_table_if_missing, get_last_processed_date, set_last_processed
from utils import get_sentinel_description, zoi
from webhook_notifier import send_webhook_notification
from email_notifier import send_email_notification


create_table_if_missing()

today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=7)

START_DATE = yesterday.strftime("%Y-%m-%d")
END_DATE = today.strftime("%Y-%m-%d")

exported_data = []

# Visualization parameters for VV (dB)
vis_params = {
    "min": -25,
    "max": -5,
    "palette": ["0000FF", "00FFFF", "00FF00", "FFFF00", "FF0000"],  # Blue to Red
}

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


# cls && .venv\Scripts\python.exe src/main_sentinel.py
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
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(zoi)
            .filterDate(new_dates[0])
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .select("VV")
        )

        logging.info("🆕  %d new dates to process.", len(new_dates))

        if len(new_dates) == 1:
            ts = f"{new_dates[0].strftime("%Y-%m-%d %H_%M")}"
        else:
            ts = f"{new_dates[0].strftime("%Y-%m-%d %H_%M")} → {new_dates[-1].strftime("%Y-%m-%d %H_%M")}"
        logging.info("From: %s", ts)
        export_table(updated_smap, ts)
    else:
        logging.info("✅ No new dates to process.")


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
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{now_str}/soil_moisture_{date_str}"

    # vv_rgb = img.clip(zoi).visualize(**vis_params)
    task = ee.batch.Export.image.toDrive(
        image=img.clip(zoi),
        description=f"soil_moisture_{date_str}",
        folder="GEE_Soil_Moisture_Moulouya",
        fileNamePrefix=filename,
        region=zoi,
        scale=10,
        maxPixels=1e9,
        fileFormat="GeoTIFF",
    )
    task.start()
    while task.active():
        logging.info("Task is running...")
        time.sleep(10)

    logging.info("Task state: %s", task.status()["state"])
    logging.info("🛰️ Export started for %s", date_str)

    # 1. Extract soil moisture mean for your ZOI on this image
    mean_dict = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=zoi,
        scale=10,
        maxPixels=1e9,
    ).getInfo()

    vv = mean_dict.get("VV", None)
    exported_data.append(
        {
            "date": date_str,
            "vv_dB": vv,
            "description": get_sentinel_description(vv),
        }
    )


def extract_vv_mean(img):
    """
    Extracts the mean VV (vertical transmit, vertical receive) backscatter value from a given Earth Engine image over a specified geometry.

    Args:
        img (ee.Image): The Earth Engine image from which to extract the mean VV value.

    Returns:
        ee.Feature: An Earth Engine Feature containing the date of the image and the mean VV value over the specified geometry.

    Note:
        - The function assumes that the variables `ee` (Earth Engine API) and `zoi` (zone of interest geometry) are defined in the global scope.
        - The returned feature has properties 'date' (formatted as 'YYYY-MM-dd') and 'vv' (mean VV value).
    """
    stats = img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=zoi, scale=10, maxPixels=1e9
    )
    return ee.Feature(
        None, {"date": img.date().format("YYYY-MM-dd"), "vv": stats.get("VV")}
    )


def export_table(smap_to_use, timestamps):
    """
    Exports a table of mean VV (vertical transmit and receive) backscatter values from a collection of features.
    This function processes a collection of features by extracting the mean VV value for each feature, filtering out any features with null VV values, and then converting the results into a pandas DataFrame.
    The resulting DataFrame contains columns for the date and the corresponding VV value in decibels (dB). The 'date' column is converted to pandas datetime objects for easier manipulation and analysis.
    The DataFrame is then printed to the console.
    Returns:
        None
    """
    features = smap_to_use.map(extract_vv_mean).filter(ee.Filter.notNull(["vv"]))
    results = features.getInfo()["features"]
    df = pd.DataFrame(
        [
            {
                "date": f["properties"]["date"],
                "vv_dB": f["properties"]["vv"],
                "description": get_sentinel_description(f["properties"]["vv"]),
            }
            for f in results
        ]
    )

    folder_path = os.path.join("exports", timestamps)
    os.makedirs(folder_path, exist_ok=True)
    combined_csv_path = f"exports/{timestamps}/soil_moisture.csv"
    df.to_csv(combined_csv_path, index=False)
    logging.info("💾 Combined CSV saved: %s", combined_csv_path)

    dataset = df.to_dict(orient="records")
    send_webhook_notification(dataset)
    send_email_notification(timestamps, combined_csv_path)
    set_last_processed(dataset)


def export_geotiff(updated_smap):
    """
    Exports the median Sentinel-1 VV image as a GeoTIFF file to Google Drive.

    This function computes the median value of the Sentinel-1 VV band image collection (to reduce noise)
    over a specified zone of interest (zoi), and exports the resulting image to a designated folder
    in Google Drive using the Earth Engine batch export functionality.

    The exported file is named with a timestamp and saved in GeoTIFF format at 10m resolution.

    Args:
        None

    Returns:
        None

    Requires:
        - The variables `updated_smap` (an Earth Engine ImageCollection) and `zoi` (the region of interest) must be defined in the global scope.
        - The Earth Engine Python API (`ee`) must be initialized.
    """
    # Compute median image (reduce noise)
    vv_median = updated_smap.median().clip(zoi)
    export_filename = f"Sentinel1_VV_{datetime.now().strftime('%Y%m%d_%H%M')}"
    task = ee.batch.Export.image.toDrive(
        image=vv_median,
        description=export_filename,
        folder="GEE_Soil_Moisture_Moulouya",
        fileNamePrefix=export_filename,
        region=zoi,
        scale=10,
        maxPixels=1e9,
        fileFormat="GeoTIFF",
        crs="EPSG:4326",
    )
    task.start()


# Run export
def run_export(updated_smap, timestamps):
    """
    Processes and exports soil moisture images from the SMAP dataset within a specified date range.
    This function retrieves a list of images from the global `updated_smap` object, checks if any images are available,
    and iterates through each image to extract data using the `extract_data` function. If no images are found,
    a warning message is printed. If an error occurs while processing an image, an error message is displayed
    with the corresponding index and exception details.
    Raises:
        ee.EEException: If an error occurs during image processing.
    """
    images = updated_smap.toList(updated_smap.size())
    image_count = updated_smap.size().getInfo()

    if image_count == 0:
        logging.info("⚠️ No images found for the specified date range.")
    else:
        for i in range(image_count):
            try:
                image = ee.Image(images.get(i))
                extract_data(image)
            except ee.EEException as e:
                logging.info("❌ Failed to process image at index %s: %s", i, e)
    bulk_notify_and_hook(timestamps)


def bulk_notify_and_hook(timestamps):
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
        logging.info("💾 Combined CSV saved: %s", combined_csv_path)

        # ✅ One-time notification
        send_webhook_notification(exported_data)
        send_email_notification(timestamps, combined_csv_path)
        set_last_processed(exported_data)
    else:
        logging.info("⚠️ No data to export or notify.")


# Run the script every 7 days
INTERVAL_DAYS = 7
INTERVAL_SECONDS = INTERVAL_DAYS * 24 * 60 * 60

if __name__ == "__main__":
    while True:
        try:
            main()
        except (ee.EEException, OSError, ValueError) as e:
            logging.info("❌ Error occurred: %s", e)
        logging.info("⏳ Sleeping for %d days...\n", INTERVAL_DAYS)
        time.sleep(INTERVAL_SECONDS)
