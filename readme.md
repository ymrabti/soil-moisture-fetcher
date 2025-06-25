# Soil Moisture Fetcher

A Python-based automation tool for fetching, processing, and exporting NASA SMAP soil moisture data for a specific Zone of Interest (ZOI) using Google Earth Engine (GEE). The project saves daily soil moisture statistics as CSV files, exports GeoTIFFs to Google Drive, and notifies via webhook and/or email.

## Features

- Fetches daily SMAP soil moisture data for a user-defined polygon (ZOI)
- Computes mean soil moisture for the ZOI and saves as CSV
- Exports clipped GeoTIFF images to Google Drive
- Sends notifications via webhook and (optionally) email with CSV report
- Dockerized for easy deployment

## Architecture

```
+-------------------+
|   [`main.py`](main.py )         |
|-------------------|
| - Loads .env      |
| - Initializes GEE |
| - Defines ZOI     |
| - Fetches SMAP    |
|   images          |
| - For each image: |
|   - Exports to    |
|     Google Drive  |
|   - Computes mean |
|   - Saves CSV     |
|   - Sends webhook |
|   - (Optionally)  |
|     sends email   |
+-------------------+
         |
         v
+-------------------+
| Google Earth      |
| Engine API        |
+-------------------+
         |
         v
+-------------------+
| Google Drive      |
+-------------------+
         |
         v
+-------------------+
| Webhook/Email     |
+-------------------+
```

## File Structure

- [`main.py`](main.py): Main script for fetching, processing, exporting, and notifying.
- [`requirements.txt`](requirements.txt): Python dependencies.
- [`Dockerfile`](Dockerfile): Docker build instructions.
- [`docker-compose.yml`](docker-compose.yml): Optional Docker Compose setup.
- [`run.bash`](run.bash): Helper script to build and run the Docker container.
- `.env.sample`: Example environment configuration.
- `.env`: Actual environment variables (not committed).
- `.gitignore`: Ignores `.env` and CSV files.
- `soil_moisture_YYYY-MM-DD.csv`: Output CSV files with daily statistics.

## Environment Variables

Copy `.env.sample` to `.env` and fill in your credentials:

- `WEBHOOK_URL`: URL to send notifications to
- `GDRIVE_FOLDER`: Google Drive folder for exports
- `SMTP_*`, `EMAIL_FROM`, `EMAIL_TO`: (Optional) Email settings for notifications

## Usage

### 1. Configure Environment

Edit `.env` with your credentials and settings.

### 2. Run with Docker

```sh
bash [`run.bash`](run.bash )
```

Or manually:

```sh
docker build -t soil-moisture-fetcher .
docker run --rm \
  -v $HOME/.config/earthengine:/root/.config/earthengine \
  --env-file .env \
  soil-moisture-fetcher
```

### 3. Run Locally (without Docker)

Install dependencies:

```sh
pip install -r [`requirements.txt`](requirements.txt )
```

Run:

```sh
python [`main.py`](main.py )
```

## Output

- CSV files: `soil_moisture_YYYY-MM-DD.csv` (mean soil moisture for ZOI)
- GeoTIFFs: Exported to your Google Drive folder
- Notifications: Sent to webhook and/or email

## Customization

- **Zone of Interest (ZOI):** Edit the polygon in [`main.py`](main.py) to match your area.
- **Date Range:** By default, fetches the last 5 days. Adjust in [`main.py`](main.py) as needed.
- **Notification:** Enable/disable email by commenting/uncommenting the relevant line in [`main.py`](main.py).

## License

MIT License

---

**Author:** Younes Mrabti  
**Contact:** mr.younes@youmrabti.com
```
soil-moisture-fetcher
├─ .pylintrc
├─ DESCRIPTION.md
├─ docker-compose.yml
├─ License
├─ readme.md
└─ src
   ├─ db.py
   ├─ Dockerfile
   ├─ email_notifier.py
   ├─ main.py
   ├─ main_sentinel.py
   ├─ requirements.txt
   ├─ test.py
   ├─ utils.py
   └─ webhook_notifier.py

```