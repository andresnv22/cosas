"""MercadoLibre Colombia.

Usa la API pública de items (no requiere token para leer precio/título):
https://api.mercadolibre.com/items/MCO123456789

El desafío no es la API, es sacar el ID del producto de la URL que te copiás
del navegador — vienen en formas bastante distintas:

  https://articulo.mercadolibre.com.co/MCO-1234567890-nombre-_JM
  https://www.mercadolibre.com.co/nombre-producto/p/MCO12345678
  https://mercadolibre.com.co/sec/1AbCdEf          (link corto)

Si no lo encontramos en la URL, bajamos el HTML y lo buscamos en la meta
`og:url` o en el JSON-LD de la página (fallback, más lento pero cubre los
links cortos).
"""

from __future__ import annotations

import re

from .base import ScrapedPrice, ScraperError, http_client

store_name = "mercadolibre"

_ITEM_ID_RE = re.compile(r"(MCO-?\d{6,})", re.IGNORECASE)


def matches(url: str) -> bool:
    return "mercadolibre.com" in url or "mercadolibre.com.co" in url


def _normalize_item_id(raw: str) -> str:
    return raw.upper().replace("-", "")


def _extract_item_id_from_url(url: str) -> str | None:
    match = _ITEM_ID_RE.search(url)
    return _normalize_item_id(match.group(1)) if match else None


def _extract_item_id_from_html(url: str) -> str:
    """Fallback para links cortos (mercadolibre.com.co/sec/...): seguimos el
    redirect y buscamos el ID en la página final."""
    with http_client() as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

    # 1) La URL final después de seguir redirects suele tener el ID
    item_id = _extract_item_id_from_url(str(resp.url))
    if item_id:
        return item_id

    # 2) Buscar en el HTML (og:url, JSON-LD, o cualquier mención directa)
    item_id = _extract_item_id_from_url(html)
    if item_id:
        return item_id

    raise ScraperError(f"No pude encontrar el ID de producto en {url}")


def fetch(url: str) -> ScrapedPrice:
    item_id = _extract_item_id_from_url(url) or _extract_item_id_from_html(url)

    api_url = f"https://api.mercadolibre.com/items/{item_id}"
    with http_client() as client:
        resp = client.get(api_url)
        if resp.status_code == 404:
            raise ScraperError(f"MercadoLibre no encontró el producto {item_id} (¿se dio de baja?)")
        resp.raise_for_status()
        data = resp.json()

    title = data.get("title", item_id)
    price = data.get("price")
    currency = data.get("currency_id", "COP")
    available_qty = data.get("available_quantity", 0)
    status = data.get("status", "active")

    if price is None:
        raise ScraperError(f"MercadoLibre no devolvió precio para {item_id}")

    in_stock = status == "active" and available_qty > 0

    return ScrapedPrice(title=title, price=float(price), currency=currency, in_stock=in_stock)
