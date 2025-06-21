"""
This module provides functions to interact with a PostgreSQL database for tracking soil moisture data.
Functions:
    get_connection():
        Establishes and returns a new connection to the PostgreSQL database using environment variables for configuration.
    get_last_processed_date():
        Retrieves the most recent 'last_date' entry from the 'soil_state' table.
        Returns:
            The last processed date as stored in the database, or None if no entry exists.
    set_last_processed(date_str, moisture_value):
        Inserts a new record into the 'soil_state' table with the provided date and moisture value.
        Args:
            date_str (str): The date to record as the last processed date.
            moisture_value (float): The corresponding soil moisture value.
"""

import os
import psycopg2


def create_table_if_missing():
    """
    Creates the 'soil_state' table in the database if it does not already exist.

    The table includes the following columns:
        - id: Auto-incrementing primary key.
        - last_date: Date of the soil state record (required).
        - moisture: Floating-point value representing soil moisture.
        - created_at: Timestamp of when the record was created (defaults to current timestamp).

    Commits the transaction after attempting to create the table.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS soil_state (
                    id SERIAL PRIMARY KEY,
                    last_date DATE NOT NULL,
                    moisture FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()


def get_connection():
    """
    Establishes and returns a connection to a PostgreSQL database using credentials and connection details
    retrieved from environment variables.

    Environment Variables:
        DB_HOST (str): The hostname of the database server.
        DB_PORT (str): The port number on which the database server is listening.
        DB_NAME (str): The name of the database to connect to.
        DB_USER (str): The username used to authenticate with the database.
        DB_PASS (str): The password used to authenticate with the database.

    Returns:
        psycopg2.extensions.connection: A new database connection object.

    Raises:
        psycopg2.OperationalError: If the connection to the database fails.
    """
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
    )


def get_last_processed_date():
    """
    Retrieves the most recent 'last_date' entry from the 'soil_state' table in the database.

    Returns:
        datetime or None: The latest processed date if available; otherwise, None.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT last_date FROM soil_state ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            return row[0] if row else None


def set_last_processed(date_str, moisture_value):
    """
    Inserts a new record into the 'soil_state' table with the provided date and moisture value.

    Args:
        date_str (str): The date string representing the last processed date.
        moisture_value (float): The soil moisture value to be stored.

    Raises:
        Exception: If there is an error during database insertion.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO soil_state (last_date, moisture) VALUES (%s, %s)",
                (date_str, moisture_value),
            )
            conn.commit()
