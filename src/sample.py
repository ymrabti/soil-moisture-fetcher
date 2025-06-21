"""
This script fetches and processes soil moisture data, updating the last processed date and value in the database.
Workflow:
1. Imports necessary modules for date handling and database operations.
2. Prints a startup message.
3. Retrieves the last processed date from the database and prints it.
4. Gets the current UTC date.
5. (Placeholder) Assigns a sample soil moisture value; replace with actual data processing logic.
6. Updates the database with the current date and new soil moisture value.
7. Prints a confirmation message with the saved date and moisture value.
Dependencies:
- db module with `get_last_processed_date` and `set_last_processed` functions.
"""

from datetime import datetime, timezone
from db import get_last_processed_date, set_last_processed, create_table_if_missing

print("🚀 Starting soil fetcher")
create_table_if_missing()
last = get_last_processed_date()
print(f"🔁 Last processed: {last}")

today = datetime.now(tz=timezone.utc).date().isoformat()
MOISTURE_DATA = 0.123  # ← replace with actual processing
set_last_processed(today, MOISTURE_DATA)

print(f"✅ Saved {today} with moisture={MOISTURE_DATA}")
