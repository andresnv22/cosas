"""Amazon (amazon.com, .es, .com.mx, .co.uk, .de, .ca, .com.br, ...).

Amazon no tiene API pública de precios (la PA-API exige cuenta de
afiliado con ventas), así que esto lee el HTML de la página del producto.
Es el scraper más frágil de todos, por dos motivos:

1. Anti-bot: a veces devuelve un captcha ("Robot Check") o un 503 en vez
   de la página. Lo detectamos y reintentamos con espera; si sigue, falla
   con un error claro en vez de guardar un precio basura.
2. La página tiene VARIOS precios. El que importa es el de la caja de
   compra. Ojo con `#corePriceDisplay_desktop_feature_div` / `#apex_desktop`:
   ahí aparece el precio "de lista" tachado (ej: Echo Dot muestra US$79.99
   tachado y se paga US$39.99). Por eso el orden de selectores de abajo
   importa y tiene un test de regresión.
"""

from __future__ import annotations

import re
import time
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import ScrapedPrice, ScraperError, http_client

store_name = "amazon"

_ASIN_RE = re.compile(
    r"/(?:dp|gp/product|gp/aw/d|exec/obidos/ASIN|o/ASIN)/([A-Z0-9]{10})(?:[/?#]|$)",
    re.IGNORECASE,
)
_SHORT_HOSTS = ("amzn.to", "a.co", "amzn.eu", "amzn.asia")

# En orden de confianza. El primer selector que devuelva un precio no vacío gana.
_PRICE_SELECTORS = (
    "#tp_price_block_total_price_ww .a-offscreen",   # caja de compra: lo que pagás
    "#corePrice_feature_div .a-offscreen",
    "#corePrice_desktop .a-price .a-offscreen",
    "#priceblock_dealprice",
    "#priceblock_ourprice",
    "#price_inside_buybox",
)

_UNAVAILABLE_PHRASES = (
    "no disponible",
    "currently unavailable",
    "agotado",
    "out of stock",
    "temporarily out of stock",
    "non disponibile",
    "nicht verfügbar",
    "indisponível",
)

_CURRENCY_BY_TLD = {
    "com": "USD",
    "ca": "CAD",
    "com.mx": "MXN",
    "com.br": "BRL",
    "co.uk": "GBP",
    "es": "EUR",
    "de": "EUR",
    "fr": "EUR",
    "it": "EUR",
    "nl": "EUR",
    "co.jp": "JPY",
    "in": "INR",
    "com.au": "AUD",
}

_MAX_ATTEMPTS = 3


def matches(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host.startswith("amazon.") or ".amazon." in host or host in _SHORT_HOSTS


def _tld(host: str) -> str:
    """'www.amazon.com.mx' -> 'com.mx'"""
    host = host.lower()
    idx = host.find("amazon.")
    return host[idx + len("amazon."):] if idx != -1 else "com"


def extract_asin(url: str) -> str | None:
    match = _ASIN_RE.search(url)
    return match.group(1).upper() if match else None


def canonical_url(url: str) -> str:
    """'https://www.amazon.com/Echo/dp/B09B8V1LZ3/ref=sr_1?crid=..' ->
    'https://www.amazon.com/dp/B09B8V1LZ3'. Así el mismo producto pegado con
    distinto tracking no se guarda dos veces. Links cortos (amzn.to) quedan
    igual: resolverlos necesita pegarle a internet."""
    host = (urlparse(url).hostname or "").lower()
    asin = extract_asin(url)
    if not asin or host in _SHORT_HOSTS:
        return url
    return f"https://{host}/dp/{asin}"


def parse_price(text: str) -> float | None:
    """Convierte 'US$1,249.00', '1.249,00 €', '$ 39.99', 'R$ 1.299,90' en float.

    Regla: el último separador (',' o '.') seguido de exactamente 1-2 dígitos
    al final es el decimal; cualquier otro separador es de miles. Así anda
    igual para formatos en inglés y en español sin depender del dominio.
    """
    digits = re.sub(r"[^\d.,]", "", text or "")
    if not digits or not re.search(r"\d", digits):
        return None

    decimal_match = re.search(r"[.,](\d{1,2})$", digits)
    if decimal_match:
        integer_part = re.sub(r"[.,]", "", digits[: decimal_match.start()])
        return float(f"{integer_part or 0}.{decimal_match.group(1)}")
    return float(re.sub(r"[.,]", "", digits))


def _is_captcha(status_code: int, html: str) -> bool:
    if status_code == 503:
        return True
    lowered = html[:20000].lower()
    return "validatecaptcha" in lowered or "robot check" in lowered or "type the characters you see" in lowered


def parse_product_page(html: str, currency: str) -> ScrapedPrice:
    """Separado del fetch para poder testearlo con HTML guardado."""
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("#productTitle")
    title = title_el.get_text(strip=True) if title_el else "Producto de Amazon"

    availability_el = soup.select_one("#availability")
    availability = availability_el.get_text(" ", strip=True).lower() if availability_el else ""
    unavailable = any(phrase in availability for phrase in _UNAVAILABLE_PHRASES)

    price = None
    for selector in _PRICE_SELECTORS:
        for element in soup.select(selector):
            price = parse_price(element.get_text(strip=True))
            if price:
                break
        if price:
            break

    if price is None:
        if unavailable:
            return ScrapedPrice(title=title, price=0.0, currency=currency, in_stock=False)
        raise ScraperError(
            "Amazon no mostró un precio en la página (puede que haya que elegir "
            "talla/color, o que solo lo vendan terceros en 'Ver opciones de compra')."
        )

    return ScrapedPrice(title=title, price=price, currency=currency, in_stock=not unavailable)


def _resolve(url: str, client) -> tuple[str, str]:
    """Devuelve (asin, host). Sigue links cortos tipo amzn.to."""
    host = (urlparse(url).hostname or "").lower()
    asin = extract_asin(url)
    if asin and host not in _SHORT_HOSTS:
        return asin, host

    resp = client.get(url)
    final_url = str(resp.url)
    asin = extract_asin(final_url)
    if not asin:
        raise ScraperError(f"No pude encontrar el código del producto (ASIN) en {url}")
    return asin, (urlparse(final_url).hostname or "www.amazon.com").lower()


def fetch(url: str) -> ScrapedPrice:
    with http_client() as client:
        client.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            }
        )
        asin, host = _resolve(url, client)
        currency = _CURRENCY_BY_TLD.get(_tld(host), "USD")
        # URL canónica: sin parámetros de tracking, más estable para Amazon.
        product_url = f"https://{host}/dp/{asin}"

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            resp = client.get(product_url)
            if resp.status_code == 404:
                raise ScraperError(f"Amazon dice que el producto {asin} no existe (404)")
            if not _is_captcha(resp.status_code, resp.text):
                resp.raise_for_status()
                return parse_product_page(resp.text, currency)
            if attempt < _MAX_ATTEMPTS:
                time.sleep(5 * attempt)

    raise ScraperError(
        f"Amazon devolvió un captcha anti-bot {_MAX_ATTEMPTS} veces seguidas para {asin}. "
        "Suele ser temporal: el próximo chequeo lo vuelve a intentar."
    )
