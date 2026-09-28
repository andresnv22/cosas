"""Steam: la tienda más fácil de todas porque tiene API pública y gratis.
No hay que scrapear HTML ni pelearse con JavaScript.

Doc no oficial pero estable desde hace años:
https://store.steampowered.com/api/appdetails?appids=<id>&cc=co&l=spanish
"""

from __future__ import annotations

import re

from .base import ScrapedPrice, ScraperError, http_client

_APPID_RE = re.compile(r"store\.steampowered\.com/app/(\d+)")

store_name = "steam"


def matches(url: str) -> bool:
    return "store.steampowered.com/app/" in url


def _extract_appid(url: str) -> str:
    match = _APPID_RE.search(url)
    if not match:
        raise ScraperError(f"No pude sacar el appid de esta URL de Steam: {url}")
    return match.group(1)


def fetch(url: str) -> ScrapedPrice:
    appid = _extract_appid(url)
    api_url = "https://store.steampowered.com/api/appdetails"
    # cc=co -> precios en pesos colombianos; l=spanish -> nombres en español
    params = {"appids": appid, "cc": "co", "l": "spanish"}

    with http_client() as client:
        resp = client.get(api_url, params=params)
        resp.raise_for_status()
        data = resp.json()

    entry = data.get(appid)
    if not entry or not entry.get("success"):
        raise ScraperError(f"Steam no devolvió datos para el appid {appid}")

    app = entry["data"]
    title = app.get("name", f"Steam app {appid}")

    if app.get("is_free"):
        return ScrapedPrice(title=title, price=0.0, currency="COP", in_stock=True)

    price_overview = app.get("price_overview")
    if not price_overview:
        # juego retirado de la tienda, o solo disponible en otra región
        return ScrapedPrice(title=title, price=0.0, currency="COP", in_stock=False)

    # Steam devuelve el precio en centavos (final = con descuento aplicado)
    price = price_overview["final"] / 100
    currency = price_overview.get("currency", "COP")

    return ScrapedPrice(title=title, price=price, currency=currency, in_stock=True)
