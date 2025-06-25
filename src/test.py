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
import json
import ee


today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=7)

START_DATE = yesterday.strftime("%Y-%m-%d")
END_DATE = today.strftime("%Y-%m-%d")

SERVICE_ACCOUNT_PATH = os.path.join(
    os.path.dirname(__file__), "gee-service-account.json"
)
FOLDER_NAME = "GEE_Soil_Moisture_Moulouya"

logging.basicConfig(level=logging.INFO)

with open(SERVICE_ACCOUNT_PATH, 'r', encoding='utf-8') as f:
    credentials = ee.ServiceAccountCredentials(
        json.load(f)["client_email"], SERVICE_ACCOUNT_PATH
    )

ee.Initialize(credentials)
logging.info("✅ Earth Engine initialisé.")

# Petite région (polygon random)
region = ee.Geometry.Rectangle([-5.2, 34.9, -5.1, 35.0])
# Image de test
image = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(region)
    .filterDate(START_DATE, END_DATE)
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    .select("VV")
)


task = ee.batch.Export.image.toDrive(
    image=ee.Image(image.first()).clip(region),
    description="test_export",
    folder=FOLDER_NAME,
    fileNamePrefix="test_image",
    region=region,
    scale=100,
    fileFormat="GeoTIFF",
)

task.start()
logging.info("📤 Tâche lancée.")

while task.active():
    logging.info("⏳ En cours...")
    time.sleep(10)

logging.info("🎯 Statut final :")
pprint.pprint(task.status())
