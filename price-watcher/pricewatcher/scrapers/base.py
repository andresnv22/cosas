"""Contrato común que cumple cada scraper de tienda.

Agregar una tienda nueva = crear un archivo acá adentro con una clase que
herede de `Scraper` e implemente `fetch`. Nada más del sistema necesita
saber que existe: `checker.py` los descubre por el diccionario `SCRAPERS`
en `__init__.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

import httpx

from .. import config


@dataclass
class ScrapedPrice:
    title: str
    price: float
    currency: str
    in_stock: bool = True


class ScraperError(Exception):
    """El scraper no pudo extraer un precio confiable de la página."""


class Scraper(Protocol):
    store_name: str

    def matches(self, url: str) -> bool:
        """¿Esta URL le pertenece a esta tienda?"""
        ...

    def fetch(self, url: str) -> ScrapedPrice:
        """Trae el precio actual. Lanza ScraperError si no pudo."""
        ...


def http_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": config.USER_AGENT, "Accept-Language": "es-CO,es;q=0.9"},
        timeout=config.REQUEST_TIMEOUT,
        follow_redirects=True,
    )
