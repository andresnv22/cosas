"""Genera el gráfico de precio que se manda junto con cada alerta.
matplotlib con backend 'Agg' porque esto corre sin pantalla (cron / GH Actions).
"""

from __future__ import annotations

import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402

from . import db, money  # noqa: E402

# Paleta simple y consistente. Nada de colores default de matplotlib.
_BG = "#0f172a"
_FG = "#e2e8f0"
_LINE = "#38bdf8"
_MARK_LOW = "#4ade80"
_GRID = "#1e293b"


def price_history_chart(product: db.Product, days: int = 90, db_path=None) -> bytes:
    history = db.price_history(product.id, days=days, db_path=db_path)
    if not history:
        raise ValueError("No hay historial para graficar todavía.")

    # Los registros sin stock se guardan con precio 0: graficarlos hunde la
    # curva a cero y el "mínimo" sería falso. Solo puntos con stock.
    history = [p for p in history if p.in_stock]
    if not history:
        raise ValueError("No hay precios con stock para graficar todavía.")
    currency = history[-1].currency

    dates = [datetime.fromisoformat(p.checked_at) for p in history]
    prices = [p.price for p in history]

    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)

    ax.plot(dates, prices, color=_LINE, linewidth=2, marker="o", markersize=3)

    min_price = min(prices)
    min_idx = prices.index(min_price)
    ax.scatter([dates[min_idx]], [min_price], color=_MARK_LOW, s=60, zorder=5, label=f"Mínimo: {money.fmt(min_price, currency)}")

    ax.set_title(product.title or product.url, color=_FG, fontsize=11, pad=12)
    ax.tick_params(colors=_FG, labelsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.autofmt_xdate()

    for spine in ax.spines.values():
        spine.set_color(_GRID)
    ax.grid(True, color=_GRID, linewidth=0.6)
    ax.legend(facecolor=_BG, labelcolor=_FG, fontsize=8, loc="upper right")

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: money.fmt(x, currency)))

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", facecolor=_BG)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
