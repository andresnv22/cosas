"""Utilidades de texto. Separado en su propio módulo porque lo usan tanto
`bot.py` como `checker.py` y no quería que ninguno dependiera del otro.
"""

from __future__ import annotations

# Legacy Markdown de Telegram (parse_mode="Markdown", no MarkdownV2) solo
# necesita escapar estos cuatro caracteres. Sin esto, un título de producto
# con un guion bajo o un corchete (frecuentísimo en MercadoLibre: "Combo x2
# [Envío gratis]") rompe el parser y Telegram devuelve un 400 — el mensaje
# ni se manda.
_MARKDOWN_SPECIAL = ("_", "*", "`", "[")


def escape_markdown(text: str) -> str:
    for char in _MARKDOWN_SPECIAL:
        text = text.replace(char, f"\\{char}")
    return text
