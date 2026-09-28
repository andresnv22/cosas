"""Bot interactivo de Telegram. El cron (`checker.py`) hace el trabajo pesado
en background; este bot es la interfaz para agregar/listar/borrar productos
y pedir el historial a demanda.

Correr localmente: `python -m pricewatcher.bot`
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from . import charts, config, db
from .scrapers import ScraperError, find_scraper_for, store_names
from .textutil import escape_markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bot")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    tiendas = ", ".join(store_names())
    await update.message.reply_text(
        "👋 Soy tu vigilante de precios.\n\n"
        f"Tiendas soportadas: {tiendas}\n\n"
        "*/watch <url>* — seguir un producto\n"
        "*/watch <url> <precio>* — avisarme cuando llegue a ese precio\n"
        "*/list* — ver lo que estoy siguiendo\n"
        "*/history <id>* — gráfico de precio\n"
        "*/unwatch <id>* — dejar de seguir\n\n"
        f"Tu chat_id es `{chat_id}` (por si necesitás configurarlo a mano en el cron).",
        parse_mode=ParseMode.MARKDOWN,
    )


async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    args = context.args

    if not args:
        await update.message.reply_text("Uso: /watch <url> [precio objetivo]")
        return

    url = args[0]
    target_price = None
    if len(args) > 1:
        try:
            target_price = float(args[1].replace(",", "").replace("$", ""))
        except ValueError:
            await update.message.reply_text("El precio objetivo tiene que ser un número, ej: /watch <url> 150000")
            return

    scraper = find_scraper_for(url)
    if scraper is None:
        await update.message.reply_text(
            f"No reconozco esa tienda. Por ahora soporto: {', '.join(store_names())}"
        )
        return

    await update.message.reply_text("🔎 Consultando el precio actual...")

    try:
        scraped = scraper.fetch(url)
    except ScraperError as exc:
        await update.message.reply_text(f"No pude leer el precio: {exc}")
        return

    product = db.add_product(
        url=url,
        store=scraper.store_name,
        chat_id=chat_id,
        title=scraped.title,
        target_price=target_price,
    )
    db.record_price(product.id, scraped.price, scraped.currency, scraped.in_stock)

    extra = f"\n🎯 Te aviso cuando llegue a ${target_price:,.0f}" if target_price else ""
    safe_title = escape_markdown(scraped.title)
    await update.message.reply_text(
        f"✅ Siguiendo *{safe_title}*\nPrecio actual: ${scraped.price:,.0f} {scraped.currency}\nID: {product.id}{extra}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    products = db.list_products(chat_id=chat_id)

    if not products:
        await update.message.reply_text("No estás siguiendo nada todavía. Usá /watch <url>.")
        return

    lines = []
    for p in products:
        last = db.last_price(p.id)
        price_str = f"${last.price:,.0f}" if last else "sin datos aún"
        safe_title = escape_markdown(p.title or p.url)
        lines.append(f"*{p.id}* — {safe_title}\n  {price_str} ({p.store})")

    await update.message.reply_text("\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def unwatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    args = context.args

    if not args or not args[0].isdigit():
        await update.message.reply_text("Uso: /unwatch <id> (el id lo ves con /list)")
        return

    product_id = int(args[0])
    ok = db.deactivate_product(product_id, chat_id)
    if ok:
        await update.message.reply_text(f"❌ Dejé de seguir el producto {product_id}.")
    else:
        await update.message.reply_text("No encontré ese producto en tu lista.")


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    args = context.args

    if not args or not args[0].isdigit():
        await update.message.reply_text("Uso: /history <id>")
        return

    product_id = int(args[0])
    product = db.get_product(product_id)
    if not product or product.chat_id != chat_id:
        await update.message.reply_text("No encontré ese producto en tu lista.")
        return

    points = db.price_history(product_id)
    if len(points) < 2:
        await update.message.reply_text("Todavía no tengo suficiente historial para graficar (esperá al próximo chequeo).")
        return

    chart_bytes = charts.price_history_chart(product)
    await update.message.reply_photo(photo=chart_bytes, caption=product.title or product.url)


def build_app() -> Application:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN. Mirá el .env.example.")

    db.init_db()

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(CommandHandler("list", list_products))
    app.add_handler(CommandHandler("unwatch", unwatch))
    app.add_handler(CommandHandler("history", history))
    return app


def main() -> None:
    app = build_app()
    log.info("Bot corriendo (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
