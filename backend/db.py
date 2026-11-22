import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load the .env file that sits next to this file, and let it override any existing value
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )