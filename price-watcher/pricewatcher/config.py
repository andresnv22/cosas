"""Configuración central: todo sale de variables de entorno.

En local, poné estas variables en un archivo `.env` (mirá `.env.example`).
En GitHub Actions, se cargan desde Settings → Secrets and variables → Actions.
"""

from __future__ import annotations

import os
from pathlib import Path

# Carga .env solo si existe (no falla si no está python-dotenv en producción)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
# Chat al que se mandan las alertas automáticas (el cron no puede "responder"
# a nadie, así que necesita saber a quién escribirle). Se obtiene la primera
# vez que le hablás al bot con /start.
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- Base de datos ---
DB_PATH = Path(os.environ.get("PRICEWATCHER_DB", BASE_DIR / "data" / "pricewatcher.db"))

# --- Scraping ---
# User-Agent de navegador real: varios sitios devuelven HTML distinto (o un
# bloqueo) a clientes que se identifican como bots.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20  # segundos

# Umbral para avisar: hay que bajar al menos esto para que valga la pena
# molestarte. Evita alertas por un peso de diferencia.
MIN_DROP_PERCENT = float(os.environ.get("MIN_DROP_PERCENT", "3"))

# Cuántos días de historial mirar para decidir si un "descuento" es real
FAKE_DISCOUNT_WINDOW_DAYS = int(os.environ.get("FAKE_DISCOUNT_WINDOW_DAYS", "90"))
