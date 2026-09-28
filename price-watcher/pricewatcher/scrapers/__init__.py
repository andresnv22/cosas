"""Registro de scrapers disponibles.

Para agregar una tienda nueva: creá `mitienda.py` en esta carpeta con
`store_name`, `matches(url)` y `fetch(url)`, y agregala a la lista `_MODULES`
de abajo. Todo lo demás (cron, bot, base de datos) la reconoce solo.
"""

from __future__ import annotations

from . import mercadolibre, steam
from .base import ScrapedPrice, ScraperError

_MODULES = [mercadolibre, steam]


def find_scraper_for(url: str):
    """Devuelve el módulo scraper que sabe manejar esta URL, o None."""
    for module in _MODULES:
        if module.matches(url):
            return module
    return None


def store_names() -> list[str]:
    return [m.store_name for m in _MODULES]


__all__ = ["find_scraper_for", "store_names", "ScrapedPrice", "ScraperError"]
