#!/usr/bin/env python3
"""Valida tu .env antes de confiar en las alertas. Corré esto después de
completar SMTP_USER/SMTP_PASSWORD/EMAIL_TO — te dice exactamente qué falla,
en vez de que lo descubras cuando una alerta real no te llegue.

Uso: python scripts/verify_setup.py
"""

from __future__ import annotations

import smtplib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricewatcher import config, notify  # noqa: E402

OK = "✅"
FAIL = "❌"
WARN = "⚠️ "


def check_config() -> bool:
    missing = []
    if not config.SMTP_USER:
        missing.append("SMTP_USER")
    if not config.SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    if not config.EMAIL_TO:
        missing.append("EMAIL_TO")

    if missing:
        print(f"{FAIL} Falta completar en .env: {', '.join(missing)}")
        return False

    print(f"{OK} SMTP_USER, SMTP_PASSWORD y EMAIL_TO están completos")
    print(f"   Servidor: {config.SMTP_HOST}:{config.SMTP_PORT}")
    print(f"   De: {config.EMAIL_FROM}  →  Para: {config.EMAIL_TO}")
    return True


def check_smtp_login() -> bool:
    try:
        server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15)
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.quit()
    except smtplib.SMTPAuthenticationError:
        print(f"{FAIL} El servidor rechazó el usuario/contraseña (SMTPAuthenticationError)")
        print("   Con Gmail: ¿generaste una 'contraseña de aplicación'? La contraseña")
        print("   normal de la cuenta no funciona si tenés verificación en 2 pasos.")
        return False
    except (smtplib.SMTPException, OSError) as exc:
        print(f"{FAIL} No pude conectar/loguear al servidor SMTP: {exc}")
        return False

    print(f"{OK} Login SMTP exitoso")
    return True


def check_send_test_email() -> bool:
    try:
        notify.send_test_email()
    except Exception as exc:  # noqa: BLE001
        print(f"{FAIL} El login funcionó pero no pude mandar el mail de prueba: {exc}")
        return False

    print(f"{OK} Mail de prueba enviado a {config.EMAIL_TO} — revisá tu bandeja (y spam)")
    return True


def main() -> int:
    print("Verificando price-watcher/.env...\n")

    if not check_config():
        print(f"\n{WARN} Completá el .env antes de seguir.")
        return 1

    print()
    if not check_smtp_login():
        return 1

    print()
    if not check_send_test_email():
        return 1

    print(f"\n{OK} Todo listo. Agregá productos con: python -m pricewatcher.cli watch <url>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
