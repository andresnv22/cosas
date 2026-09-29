from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent


def _env(name: str, default: str) -> str:
    """os.environ.get(name, default) normal solo cubre la variable ausente.
    Si esto corre alguna vez con secrets de GitHub Actions: un secret no
    configurado se inyecta como string VACÍO (no ausente), y `os.environ.get`
    devolvería "" en vez del default — con `float("")` eso explota. Trata
    "ausente" y "vacío" igual."""
    return os.environ.get(name) or default


CALENDAR_ICS_URL = _env("CALENDAR_ICS_URL", "")

LATITUDE = float(_env("LATITUDE", "4.7110"))   # default: Bogotá
LONGITUDE = float(_env("LONGITUDE", "-74.0721"))

# Token simple para que no cualquiera en internet pueda pegarle a tu endpoint
# y ver tu agenda. El ESP32 lo manda como header `X-Panel-Token`.
PANEL_TOKEN = _env("PANEL_TOKEN", "")

TASKS_PATH = Path(_env("TASKS_PATH", str(BASE_DIR / "data" / "tasks.json")))
