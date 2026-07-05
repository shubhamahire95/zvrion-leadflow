"""Application settings shared by the CLI and local web UI."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
HISTORY_FILE = DATA_DIR / "history.json"
LOCATIONS_FILE = DATA_DIR / "locations.json"
HOST, PORT = "127.0.0.1", 8765
DEFAULT_STATE, DEFAULT_MIN_RATING, DEFAULT_MAX_RESULTS = "Maharashtra", 0.0, 50
NAVIGATION_TIMEOUT_MS, SCROLL_ROUNDS = 45_000, 20
OUTPUT_COLUMNS = ["business_name", "category", "phone", "whatsapp_phone", "rating", "reviews",
                  "address", "city", "district", "state", "website", "maps_link"]
