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

# --- Email (SMTP) ---
# Con Gmail: activá verificación en 2 pasos y generá una "contraseña de
# aplicación" en myaccount.google.com/apppasswords — la contraseña normal
# de tu cuenta NO funciona para SMTP si tenés 2FA activado (y si no lo
# tenés, activalo).
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
# De dónde sale el mail. Si no lo seteás, usa SMTP_USER (lo normal).
EMAIL_FROM = os.environ.get("EMAIL_FROM", "") or SMTP_USER
# A quién le llega. Podés poner varias direcciones separadas por coma.
EMAIL_TO = os.environ.get("EMAIL_TO", "")

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
