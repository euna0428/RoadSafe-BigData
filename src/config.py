from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "outputs"

load_dotenv(BASE_DIR / ".env")

SERVICE_KEY = os.getenv("KMA_SERVICE_KEY") or os.getenv("SERVICE_KEY") or "YOUR_API_KEY_HERE"
