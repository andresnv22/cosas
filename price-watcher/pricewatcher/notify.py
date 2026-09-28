"""Envío de mensajes a Telegram. Se usa tanto desde el bot interactivo como
desde el checker que corre en cron (que no tiene una conversación activa,
solo un chat_id guardado).
"""

from __future__ import annotations

import httpx

from . import config


def _api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}"


def send_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN no está configurado.")
    resp = httpx.post(
        _api_url("sendMessage"),
        json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True},
        timeout=15,
    )
    resp.raise_for_status()


def send_photo(chat_id: str, photo_bytes: bytes, caption: str = "") -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN no está configurado.")
    resp = httpx.post(
        _api_url("sendPhoto"),
        data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"},
        files={"photo": ("chart.png", photo_bytes, "image/png")},
        timeout=30,
    )
    resp.raise_for_status()
