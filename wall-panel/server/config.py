from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent

CALENDAR_ICS_URL = os.environ.get("CALENDAR_ICS_URL", "")

LATITUDE = float(os.environ.get("LATITUDE", "4.7110"))   # default: Bogotá
LONGITUDE = float(os.environ.get("LONGITUDE", "-74.0721"))

# Token simple para que no cualquiera en internet pueda pegarle a tu endpoint
# y ver tu agenda. El ESP32 lo manda como header `X-Panel-Token`.
PANEL_TOKEN = os.environ.get("PANEL_TOKEN", "")

TASKS_PATH = Path(os.environ.get("TASKS_PATH", BASE_DIR / "data" / "tasks.json"))
