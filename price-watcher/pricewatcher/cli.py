"""CLI para administrar qué productos seguís. Como las alertas van por
email (no hay chat que te conteste), agregar/sacar productos se hace acá,
a mano, corriendo esto en tu PC.

Uso:
    python -m pricewatcher.cli watch <url> [precio_objetivo]
    python -m pricewatcher.cli list
    python -m pricewatcher.cli unwatch <id>
    python -m pricewatcher.cli history <id> [archivo_salida.png]
"""

from __future__ import annotations

import argparse
import sys

from . import charts, db
from .scrapers import ScraperError, find_scraper_for, store_names


def cmd_watch(args: argparse.Namespace) -> int:
    url = args.url
    target_price = args.target_price

    scraper = find_scraper_for(url)
    if scraper is None:
        print(f"No reconozco esa tienda. Tiendas soportadas: {', '.join(store_names())}")
        return 1

    print("Consultando el precio actual...")
    try:
        scraped = scraper.fetch(url)
    except ScraperError as exc:
        print(f"No pude leer el precio: {exc}")
        return 1

    db.init_db()
    product = db.add_product(url=url, store=scraper.store_name, title=scraped.title, target_price=target_price)
    db.record_price(product.id, scraped.price, scraped.currency, scraped.in_stock)

    print(f"✅ Siguiendo [{product.id}] {scraped.title}")
    print(f"   Precio actual: ${scraped.price:,.0f} {scraped.currency}")
    if target_price:
        print(f"   Te avisa cuando llegue a ${target_price:,.0f} o menos")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    db.init_db()
    products = db.list_products()
    if not products:
        print("No estás siguiendo nada todavía. Usá: watch <url>")
        return 0

    for p in products:
        last = db.last_price(p.id)
        price_str = f"${last.price:,.0f}" if last else "sin datos aún"
        target = f" (objetivo: ${p.target_price:,.0f})" if p.target_price else ""
        print(f"[{p.id}] {p.title or p.url}")
        print(f"      {price_str} · {p.store}{target}")
    return 0


def cmd_unwatch(args: argparse.Namespace) -> int:
    db.init_db()
    if db.deactivate_product(args.id):
        print(f"❌ Dejé de seguir el producto {args.id}")
        return 0
    print(f"No encontré el producto {args.id}")
    return 1


def cmd_history(args: argparse.Namespace) -> int:
    db.init_db()
    product = db.get_product(args.id)
    if not product:
        print(f"No encontré el producto {args.id}")
        return 1

    points = db.price_history(product.id)
    if len(points) < 2:
        print("Todavía no hay suficiente historial para graficar (esperá al próximo chequeo).")
        return 1

    out_path = args.output or f"precio_{product.id}.png"
    png = charts.price_history_chart(product)
    with open(out_path, "wb") as f:
        f.write(png)
    print(f"Gráfico guardado en {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pricewatcher", description="Administrá qué productos seguís.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_watch = sub.add_parser("watch", help="Seguir un producto nuevo")
    p_watch.add_argument("url")
    p_watch.add_argument("target_price", type=float, nargs="?", default=None)
    p_watch.set_defaults(func=cmd_watch)

    p_list = sub.add_parser("list", help="Ver qué estás siguiendo")
    p_list.set_defaults(func=cmd_list)

    p_unwatch = sub.add_parser("unwatch", help="Dejar de seguir un producto")
    p_unwatch.add_argument("id", type=int)
    p_unwatch.set_defaults(func=cmd_unwatch)

    p_history = sub.add_parser("history", help="Guardar el gráfico de precio como PNG")
    p_history.add_argument("id", type=int)
    p_history.add_argument("output", nargs="?", default=None)
    p_history.set_defaults(func=cmd_history)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
