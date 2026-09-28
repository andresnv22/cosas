"""La parte 'inteligente': decidir si una baja de precio es real y si vale la
pena avisar. Nada de esto es magia — son comparaciones contra el historial,
que es justo por lo que importa haber estado guardando datos desde el día 1.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config, db


@dataclass
class PriceVerdict:
    should_alert: bool
    reason: str
    current_price: float
    previous_price: float | None
    min_price_window: float | None
    drop_percent: float | None
    is_all_time_low: bool


def evaluate(product: db.Product, current_price: float, in_stock: bool, db_path=None) -> PriceVerdict:
    history = db.price_history(product.id, db_path=db_path)
    previous = history[-1].price if history else None

    min_window = db.min_price(product.id, config.FAKE_DISCOUNT_WINDOW_DAYS, db_path=db_path)
    all_time_low = min((p.price for p in history if p.in_stock), default=None)

    if not in_stock:
        return PriceVerdict(
            should_alert=False,
            reason="Sin stock, no se evalúa el precio.",
            current_price=current_price,
            previous_price=previous,
            min_price_window=min_window,
            drop_percent=None,
            is_all_time_low=False,
        )

    if previous is None:
        # Primera vez que lo medimos: no hay "baja" que anunciar todavía
        return PriceVerdict(
            should_alert=False,
            reason="Primer registro de precio.",
            current_price=current_price,
            previous_price=None,
            min_price_window=min_window,
            drop_percent=None,
            is_all_time_low=True,
        )

    drop_percent = (previous - current_price) / previous * 100 if previous > 0 else 0
    is_all_time_low = all_time_low is None or current_price <= all_time_low

    # El chequeo clave contra el "descuento falso": no comparamos solo contra
    # el precio de ayer (eso lo hace cualquier tienda con su cartelito de
    # "-30%"), comparamos contra el mínimo real de los últimos N días.
    if min_window is not None and current_price >= min_window:
        if drop_percent >= config.MIN_DROP_PERCENT:
            return PriceVerdict(
                should_alert=False,
                reason=(
                    f"Bajó {drop_percent:.1f}% desde ayer, pero sigue en o por encima "
                    f"del mínimo de los últimos {config.FAKE_DISCOUNT_WINDOW_DAYS} días "
                    f"(${min_window:,.0f}). Probablemente el 'descuento' es maquillaje."
                ),
                current_price=current_price,
                previous_price=previous,
                min_price_window=min_window,
                drop_percent=drop_percent,
                is_all_time_low=False,
            )

    if drop_percent < config.MIN_DROP_PERCENT and not is_all_time_low:
        return PriceVerdict(
            should_alert=False,
            reason=f"Bajó solo {drop_percent:.1f}%, por debajo del umbral de aviso.",
            current_price=current_price,
            previous_price=previous,
            min_price_window=min_window,
            drop_percent=drop_percent,
            is_all_time_low=is_all_time_low,
        )

    reason = "Nuevo mínimo histórico." if is_all_time_low else f"Bajó {drop_percent:.1f}% y es un precio real (por debajo del mínimo reciente)."
    return PriceVerdict(
        should_alert=True,
        reason=reason,
        current_price=current_price,
        previous_price=previous,
        min_price_window=min_window,
        drop_percent=drop_percent,
        is_all_time_low=is_all_time_low,
    )
