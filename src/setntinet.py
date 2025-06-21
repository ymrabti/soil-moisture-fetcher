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
from webhook_notifier import send_webhook_notification
from email_notifier import send_email_notification

load_dotenv()
CREDENTIALS_JSON = os.getenv("EARTHENGINE_CREDENTIALS")
save_folder=os.getenv("GDRIVE_FOLDER", "GEE_Soil_Moisture")

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
    print(filename)

    # vv_rgb = img.clip(zoi).visualize(**vis_params)
    task = ee.batch.Export.image.toDrive(
        image=img.clip(zoi),
        description=f"soil_moisture_{date_str}",
        folder=save_folder,
        fileNamePrefix=filename,
        scale=10,
        region=zoi,
        maxPixels=1e13,
        fileFormat="GeoTIFF",
    )
    task.start()
    print(f"🛰️ Export started for {date_str}")

    # 1. Extract soil moisture mean for your ZOI on this image
    mean_dict = img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=zoi, scale=10, maxPixels=1e9
    ).getInfo()

    exported_data.append(
        {"date": date_str, "soil_moisture_mean": mean_dict.get("VV", None)}
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


def export_table():
    """
    Exports a table of mean VV (vertical transmit and receive) backscatter values from a collection of features.
    This function processes a collection of features by extracting the mean VV value for each feature, filtering out any features with null VV values, and then converting the results into a pandas DataFrame. 
    The resulting DataFrame contains columns for the date and the corresponding VV value in decibels (dB). The 'date' column is converted to pandas datetime objects for easier manipulation and analysis. 
    The DataFrame is then printed to the console.
    Returns:
        None
    """
    features = smap.map(extract_vv_mean).filter(ee.Filter.notNull(["vv"]))
    results = features.getInfo()["features"]
    df = pd.DataFrame(
        [
            {"date": f["properties"]["date"], "vv_dB": f["properties"]["vv"]}
            for f in results
        ]
    )

    df["date"] = pd.to_datetime(df["date"])
    print(df)


# 2️⃣ Generate a colored map of the median VV over your ZOI
def export_geotiff():
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
        - The variables `smap` (an Earth Engine ImageCollection) and `zoi` (the region of interest) must be defined in the global scope.
        - The Earth Engine Python API (`ee`) must be initialized.
    """
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


# cls && .venv\Scripts\python.exe setntinet.py
def print_available_dates():
    """
    Prints the range of available dates from the 'smap' dataset.

    This function retrieves an array of timestamps from the 'smap' object's 'system:time_start' property,
    converts the first and last timestamps to human-readable UTC date strings, and prints the range.
    If no dates are found, it prints a warning message.

    Returns:
        None
    """
    dates = smap.aggregate_array("system:time_start").getInfo()
    if dates:
        first = datetime.fromtimestamp(dates[0] / 1000, timezone.utc).strftime(
            "%Y-%m-%d %H:%M"
        )
        last = datetime.fromtimestamp(dates[-1] / 1000, timezone.utc).strftime(
            "%Y-%m-%d %H:%M"
        )
        print(f"{first} → {last}")
    else:
        print("⚠️ No images found.")


# Run export
def run_export():
    """
    Processes and exports soil moisture images from the SMAP dataset within a specified date range.
    This function retrieves a list of images from the global `smap` object, checks if any images are available,
    and iterates through each image to extract data using the `extract_data` function. If no images are found,
    a warning message is printed. If an error occurs while processing an image, an error message is displayed
    with the corresponding index and exception details.
    Raises:
        ee.EEException: If an error occurs during image processing.
    """
    images = smap.toList(smap.size())
    image_count = smap.size().getInfo()

    if image_count == 0:
        print("⚠️ No images found for the specified date range.")
    else:
        for i in range(image_count):
            try:
                image = ee.Image(images.get(i))
                extract_data(image)
            except ee.EEException as e:
                print(f"❌ Failed to process image at index {i}: {e}")


def bulk_notify_and_hook():
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
    - `send_webhook_notification(dates: List[str])`: Function to send a webhook notification.
    - `send_email_notification(mode: str, file_path: str)`: Function to send an email notification.
    """
    if exported_data:
        df = pd.DataFrame(exported_data)
        os.makedirs("exports", exist_ok=True)
        combined_csv_path = f"exports/soil_moisture_{START_DATE}_{END_DATE}.csv"
        df.to_csv(combined_csv_path, index=False)
        print(f"💾 Combined CSV saved: {combined_csv_path}")

        # ✅ One-time notification
        send_webhook_notification([d["date"] for d in exported_data])
        send_email_notification("batch", combined_csv_path)
    else:
        print("⚠️ No data to export or notify.")


run_export()
bulk_notify_and_hook()
