"""El corazón del sistema: recorre todos los productos activos, consulta el
precio actual, lo guarda, y avisa si vale la pena. Pensado para correr desde
un cron (GitHub Actions cada 6 horas) — cada ejecución es independiente,
no guarda estado en memoria entre corridas.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from . import analysis, charts, db, notify
from .scrapers import ScraperError, find_scraper_for
from .textutil import escape_markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("checker")


@dataclass
class CheckResult:
    product_id: int
    ok: bool
    alerted: bool
    detail: str


def _format_alert(product: db.Product, verdict: analysis.PriceVerdict) -> str:
    title = escape_markdown(product.title or product.url)
    lines = [f"🔔 *{title}*", ""]
    if verdict.is_all_time_low:
        lines.append("📉 Nuevo mínimo histórico")
    if verdict.previous_price:
        lines.append(f"Antes: ${verdict.previous_price:,.0f}")
    lines.append(f"Ahora: *${verdict.current_price:,.0f}*")
    if verdict.drop_percent:
        lines.append(f"Bajó {verdict.drop_percent:.1f}%")
    lines.append("")
    lines.append(verdict.reason)
    lines.append("")
    # Las URLs de MercadoLibre suelen terminar en "-_JM" y variantes: el
    # guion bajo también hay que escaparlo o rompe el parser de Markdown.
    lines.append(escape_markdown(product.url))
    return "\n".join(lines)


def check_product(product: db.Product) -> CheckResult:
    scraper = find_scraper_for(product.url)
    if scraper is None:
        return CheckResult(product.id, ok=False, alerted=False, detail="Ninguna tienda soportada reconoce esta URL.")

    try:
        scraped = scraper.fetch(product.url)
    except ScraperError as exc:
        log.warning("Producto %s: %s", product.id, exc)
        return CheckResult(product.id, ok=False, alerted=False, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - queremos que un scraper roto no tumbe todo el batch
        log.exception("Producto %s: error inesperado", product.id)
        return CheckResult(product.id, ok=False, alerted=False, detail=f"Error inesperado: {exc}")

    if not product.title and scraped.title:
        db.set_title(product.id, scraped.title)
        product.title = scraped.title

    verdict = analysis.evaluate(product, scraped.price, scraped.in_stock)
    db.record_price(product.id, scraped.price, scraped.currency, scraped.in_stock)

    if product.target_price is not None and scraped.price <= product.target_price:
        verdict.should_alert = True
        verdict.reason = f"Llegó a tu precio objetivo (${product.target_price:,.0f}) o por debajo. " + verdict.reason

    alerted = False
    if verdict.should_alert:
        text = _format_alert(product, verdict)
        try:
            history = db.price_history(product.id)
            if len(history) >= 2:
                chart_bytes = charts.price_history_chart(product)
                notify.send_photo(product.chat_id, chart_bytes, caption=text)
            else:
                notify.send_message(product.chat_id, text)
            alerted = True
        except Exception:  # noqa: BLE001 - el gráfico falló, probamos solo texto
            log.exception("No se pudo mandar el gráfico del producto %s, pruebo solo texto", product.id)
            try:
                notify.send_message(product.chat_id, text)
                alerted = True
            except Exception:  # noqa: BLE001 - Telegram caído: no debe tumbar el resto del batch
                log.exception("Tampoco se pudo mandar el mensaje de texto del producto %s", product.id)

    return CheckResult(product.id, ok=True, alerted=alerted, detail=verdict.reason)


def run_all(sleep_between: float = 2.0) -> list[CheckResult]:
    """Chequea todos los productos activos. `sleep_between` evita mandar
    requests en ráfaga a la misma tienda (buena práctica, no molesta a nadie)."""
    db.init_db()
    products = db.list_products(active_only=True)
    log.info("Chequeando %d productos activos", len(products))

    results = []
    for product in products:
        try:
            result = check_product(product)
        except Exception as exc:  # noqa: BLE001 - un producto roto no debe frenar el resto del batch
            log.exception("Fallo no controlado chequeando el producto %s", product.id)
            result = CheckResult(product.id, ok=False, alerted=False, detail=f"Fallo no controlado: {exc}")
        results.append(result)
        status = "ALERTA" if result.alerted else ("ok" if result.ok else "ERROR")
        log.info("[%s] %s: %s", status, product.title or product.url, result.detail)
        time.sleep(sleep_between)

    return results


if __name__ == "__main__":
    run_all()
