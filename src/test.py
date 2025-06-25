"""
This script exports a Sentinel-1 SAR image from Google Earth Engine (GEE) to Google Drive for a specified region.
Workflow:
1. Loads GEE service account credentials from a JSON file.
2. Initializes the Earth Engine API with the service account.
3. Selects the "HH" band from the "COPERNICUS/S1_GRD" image collection.
4. Defines a rectangular region of interest.
5. Sets up and starts an export task to Google Drive as a GeoTIFF file.
6. Monitors the export task status and logs progress.
7. Prints the final status of the export task.
Constants:
- SERVICE_ACCOUNT_PATH: Path to the GEE service account JSON file.
- FOLDER_NAME: Name of the Google Drive folder for export.
Logging:
- Logs initialization, task start, progress, and final status.
Dependencies:
- os, time, pprint, logging, json, ee (Earth Engine Python API)
"""

import os
import time
import pprint
import logging
from datetime import datetime, timedelta, timezone
from google.oauth2 import service_account
import ee

# cls && .venv\Scripts\python.exe src/test.py
today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=7)

START_DATE = yesterday.strftime("%Y-%m-%d")
END_DATE = today.strftime("%Y-%m-%d")

SERVICE_ACCOUNT_PATH = os.path.join(
    os.path.dirname(__file__), "gee-service-account.json"
)
FOLDER_NAME = "GEE_Soil_Moisture_Moulouya"

logging.basicConfig(level=logging.INFO)

with open(SERVICE_ACCOUNT_PATH, "r", encoding="utf-8") as f:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH
    ).with_scopes(
        [
            "https://www.googleapis.com/auth/earthengine",
            "https://www.googleapis.com/auth/drive",
        ]
    )

print(credentials.scopes)
ee.Initialize(credentials)
logging.info("✅ Earth Engine initialisé.")

# Petite région (polygon random)
region = ee.Geometry.Polygon(
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
# Image de test
image = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(region)
    .filterDate(START_DATE, END_DATE)
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    .select("VV")
    .mosaic()
    .clip(region)
)

task = ee.batch.Export.image.toDrive(
    image=image,
    description="Export GeoTIFF",
    folder=FOLDER_NAME,
    fileNamePrefix=START_DATE,
    region=region,
    scale=10,
    maxPixels=1e9,
    fileFormat="GeoTIFF",
    crs="EPSG:4326",
)
task.start()
logging.info("📤 Tâche lancée.")

while task.active():
    logging.info("⏳ En cours...")
    time.sleep(10)

logging.info("🎯 Statut final :")
pprint.pprint(task.status())
