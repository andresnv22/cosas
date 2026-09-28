#!/usr/bin/env python3
"""Valida tu .env antes de prender el bot de verdad. Corré esto después de
completar TELEGRAM_BOT_TOKEN y te dice exactamente qué falta o qué está mal
— en vez de que lo descubras con un bot que no contesta.

Uso: python scripts/verify_setup.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from pricewatcher import config  # noqa: E402

OK = "✅"
FAIL = "❌"
WARN = "⚠️ "


def check_token() -> bool:
    if not config.TELEGRAM_BOT_TOKEN:
        print(f"{FAIL} TELEGRAM_BOT_TOKEN está vacío en .env")
        print("   Conseguilo hablando con @BotFather en Telegram (/newbot)")
        return False

    try:
        resp = httpx.get(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe", timeout=10)
    except httpx.RequestError as exc:
        print(f"{FAIL} No pude conectar a la API de Telegram: {exc}")
        return False

    if resp.status_code == 401:
        print(f"{FAIL} TELEGRAM_BOT_TOKEN inválido (Telegram devolvió 401 Unauthorized)")
        print("   Revisá que lo copiaste completo, sin espacios extra")
        return False
    if resp.status_code != 200:
        print(f"{FAIL} Telegram devolvió un error inesperado: {resp.status_code} {resp.text}")
        return False

    bot_info = resp.json()["result"]
    print(f"{OK} TELEGRAM_BOT_TOKEN válido — el bot se llama @{bot_info['username']}")
    return True


def check_chat_id() -> bool:
    if not config.TELEGRAM_CHAT_ID:
        print(f"{WARN} TELEGRAM_CHAT_ID está vacío (el bot interactivo funciona igual,")
        print("   pero el chequeo automático por cron no va a saber a quién avisarte)")
        print("   Hablale al bot /start y copiá el chat_id que te devuelve")
        return False

    print(f"{OK} TELEGRAM_CHAT_ID configurado: {config.TELEGRAM_CHAT_ID}")
    return True


def check_chat_id_can_receive() -> bool:
    """Manda un mensaje de prueba real al chat_id configurado — la única
    forma de saber con certeza que el cron va a poder avisarte."""
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        return False

    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": "✅ price-watcher: setup verificado correctamente."},
            timeout=10,
        )
    except httpx.RequestError as exc:
        print(f"{FAIL} No pude mandar el mensaje de prueba: {exc}")
        return False

    if resp.status_code != 200:
        print(f"{FAIL} No pude mandarte el mensaje de prueba: {resp.text}")
        print("   ¿Le mandaste /start al bot primero? Sin eso no te puede escribir.")
        return False

    print(f"{OK} Mensaje de prueba enviado — revisá tu Telegram")
    return True


def main() -> int:
    print("Verificando price-watcher/.env...\n")
    token_ok = check_token()
    chat_ok = check_chat_id()

    if token_ok and chat_ok:
        check_chat_id_can_receive()

    print()
    if token_ok and chat_ok:
        print(f"{OK} Todo listo. Ya podés correr `python -m pricewatcher.bot` o el cron.")
        return 0
    else:
        print(f"{WARN} Hay pasos pendientes — revisá lo de arriba antes de confiar en las alertas.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
