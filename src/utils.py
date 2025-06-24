"""
utils.py
Utility functions for interpreting soil moisture conditions from Sentinel-1 VV backscatter values.
This module provides helper functions to classify and describe soil moisture levels based on
VV polarization backscatter (in decibels, dB), typically ranging from -25 to -5 dB. The main
function, `get_description` `get_sentinel_description`, returns a textual description of the soil moisture class for a
given VV dB value.
Soil moisture classes are defined as:
    - -25 <= vv_db < -22: Extremely Dry
    - -22 <= vv_db < -20: Very Dry
    - -20 <= vv_db < -18: Dry
    - -18 <= vv_db < -16: Slightly Moist
    - -16 <= vv_db < -14: Moist
    - -14 <= vv_db < -12: Very Moist
    - -12 <= vv_db <= -5: Saturated / Waterlogged
Author: Younes MRABTI
"""

from datetime import datetime, timezone
import os
import json
from google.oauth2 import service_account
import ee


SERVICE_ACCOUNT_PATH = "/app/gee-service-account.json"
# Vérifie d'abord que le fichier existe
# Lecture + debug facultatif
print(os.path.isfile(SERVICE_ACCOUNT_PATH))

with open(SERVICE_ACCOUNT_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
    print("== Service Account Debug ==")
    print(f"type: {data.get('type')}")
    print(f"client_email: {data.get('client_email')}")
    print(f"project_id: {data.get('project_id')}")
    print(f"private_key_id: {data.get('private_key_id')[:8]}...")
    print("===========================")

# Créer des credentials Google Auth
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_PATH, scopes=["https://www.googleapis.com/auth/earthengine"]
)

# Initialiser Earth Engine avec les credentials modernes
ee.Initialize(credentials)

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
area_m2 = zoi.area().getInfo()
print(f"Area: {area_m2 / 1e6:.2f} km²")


def get_description(vv_db):
    """
    Returns a textual description of soil moisture conditions based on the input VV dB value.

    Parameters:
        vv_db (float): The VV backscatter value in decibels (dB), typically ranging from -25 to -5.

    Returns:
        str: A description of the soil moisture class corresponding to the input value.
             Returns "Unknown moisture class" if the value does not fall within the defined ranges.

    Soil moisture classes:
        - -25 <= vv_db < -22: "1 – Extremely Dry: Hard, cracked soil; drought or bare land"
        - -22 <= vv_db < -20: "2 – Very Dry: Dry fields; low water retention"
        - -20 <= vv_db < -18: "3 – Dry: Lightly moist topsoil; early stress"
        - -18 <= vv_db < -16: "4 – Slightly Moist: Normal soil conditions; vegetated"
        - -16 <= vv_db < -14: "5 – Moist: Recently irrigated or after light rain"
        - -14 <= vv_db < -12: "6 – Very Moist: Wet surface; saturated or ponding starts"
        - -12 <= vv_db <= -5: "7 – Saturated / Waterlogged: Standing water, flooded fields, or dense canopy"
    """
    if vv_db is None:
        return "Unknown"
    if vv_db < 0.05:
        return "1 – Very Dry"
    elif vv_db < 0.1:
        return "2 – Dry"
    elif vv_db < 0.2:
        return "3 – Slightly Moist"
    elif vv_db < 0.3:
        return "4 – Moderately Moist"
    else:
        return "5 – Moist: Recently irrigated or after light rain"


def get_sentinel_description(vv_db):
    """
    Returns a textual description of soil moisture conditions based on the input VV dB value.

    Parameters:
        vv_db (float): The VV backscatter value in decibels (dB), typically ranging from -25 to -5.

    Returns:
        str: A description of the soil moisture class corresponding to the input value.
             Returns "Unknown moisture class" if the value does not fall within the defined ranges.

    Soil moisture classes:
        - -25 <= vv_db < -22: "1 – Extremely Dry: Hard, cracked soil; drought or bare land"
        - -22 <= vv_db < -20: "2 – Very Dry: Dry fields; low water retention"
        - -20 <= vv_db < -18: "3 – Dry: Lightly moist topsoil; early stress"
        - -18 <= vv_db < -16: "4 – Slightly Moist: Normal soil conditions; vegetated"
        - -16 <= vv_db < -14: "5 – Moist: Recently irrigated or after light rain"
        - -14 <= vv_db < -12: "6 – Very Moist: Wet surface; saturated or ponding starts"
        - -12 <= vv_db <= -5: "7 – Saturated / Waterlogged: Standing water, flooded fields, or dense canopy"
    """
    if -25 <= vv_db < -22:
        return "1 – Extremely Dry: Hard, cracked soil; drought or bare land"
    elif -22 <= vv_db < -20:
        return "2 – Very Dry: Dry fields; low water retention"
    elif -20 <= vv_db < -18:
        return "3 – Dry: Lightly moist topsoil; early stress"
    elif -18 <= vv_db < -16:
        return "4 – Slightly Moist: Normal soil conditions; vegetated"
    elif -16 <= vv_db < -14:
        return "5 – Moist: Recently irrigated or after light rain"
    elif -14 <= vv_db < -12:
        return "6 – Very Moist: Wet surface; saturated or ponding starts"
    elif -12 <= vv_db <= -5:
        return "7 – Saturated / Waterlogged: Standing water, flooded fields, or dense canopy"
    else:
        return "Unknown moisture class"


def print_available_dates(smap):
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
