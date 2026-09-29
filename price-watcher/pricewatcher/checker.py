"""El corazón del sistema: recorre todos los productos activos, consulta el
precio actual, lo guarda, y avisa si vale la pena. Pensado para correr desde
un cron (GitHub Actions cada 6 horas) — cada ejecución es independiente,
no guarda estado en memoria entre corridas.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from . import analysis, charts, db, money, notify
from .scrapers import ScraperError, find_scraper_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("checker")


@dataclass
class CheckResult:
    product_id: int
    ok: bool
    alerted: bool
    detail: str


def _format_alert(product: db.Product, verdict: analysis.PriceVerdict, currency: str = "COP") -> tuple[str, str]:
    """Devuelve (asunto, cuerpo) del mail. Texto plano — notify.py se encarga
    de escapar lo que haga falta para la versión HTML."""
    title = product.title or product.url

    subject_parts = ["🔔"]
    if verdict.back_in_stock:
        subject_parts.append("Volvió el stock:")
    elif verdict.hit_target:
        subject_parts.append("Llegó a tu precio objetivo:")
    elif verdict.is_all_time_low:
        subject_parts.append("Mínimo histórico:")
    else:
        subject_parts.append("Bajó de precio:")
    subject_parts.append(title[:60])
    subject = " ".join(subject_parts)

    lines = [title, ""]
    if verdict.is_all_time_low:
        lines.append("📉 Nuevo mínimo histórico")
    if verdict.previous_price:
        lines.append(f"Antes: {money.fmt(verdict.previous_price, currency)}")
    lines.append(f"Ahora: {money.fmt(verdict.current_price, currency)}")
    if verdict.drop_percent and verdict.drop_percent > 0:
        lines.append(f"Bajó {verdict.drop_percent:.1f}%")
    lines.append("")
    lines.append(verdict.reason)
    lines.append("")
    lines.append(product.url)
    body = "\n".join(lines)

    return subject, body


def _crossed_target(target: float | None, price: float, in_stock: bool, previous: float | None) -> bool:
    """Avisa solo al CRUZAR el objetivo, no en cada chequeo mientras siga
    abajo (serían 4 mails por día). Y nunca sin stock: esos registros tienen
    precio 0, que siempre es <= cualquier objetivo."""
    if target is None or not in_stock or price > target:
        return False
    return previous is None or previous > target


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

    verdict = analysis.evaluate(product, scraped.price, scraped.in_stock, currency=scraped.currency)
    db.record_price(product.id, scraped.price, scraped.currency, scraped.in_stock)

    if _crossed_target(product.target_price, scraped.price, scraped.in_stock, verdict.previous_price):
        verdict.should_alert = True
        verdict.hit_target = True
        verdict.reason = f"Llegó a tu precio objetivo ({money.fmt(product.target_price, scraped.currency)}) o por debajo. " + verdict.reason

    alerted = False
    if verdict.should_alert:
        subject, body = _format_alert(product, verdict, scraped.currency)
        try:
            in_stock_points = sum(1 for p in db.price_history(product.id) if p.in_stock)
            chart_bytes = charts.price_history_chart(product) if in_stock_points >= 2 else None
            notify.send_alert(subject, body, chart_bytes)
            alerted = True
        except Exception:  # noqa: BLE001 - el gráfico falló, probamos solo texto
            log.exception("No se pudo mandar el mail con gráfico del producto %s, pruebo sin gráfico", product.id)
            try:
                notify.send_alert(subject, body, chart_png=None)
                alerted = True
            except Exception:  # noqa: BLE001 - SMTP caído: no debe tumbar el resto del batch
                log.exception("Tampoco se pudo mandar el mail del producto %s", product.id)

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
