"""La parte 'inteligente': decidir si una baja de precio es real y si vale la
pena avisar. Nada de esto es magia — son comparaciones contra el historial,
que es justo por lo que importa haber estado guardando datos desde el día 1.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config, db, money


@dataclass
class PriceVerdict:
    should_alert: bool
    reason: str
    current_price: float
    previous_price: float | None
    min_price_window: float | None
    drop_percent: float | None
    is_all_time_low: bool
    back_in_stock: bool = False
    hit_target: bool = False  # lo marca checker.py al cruzar el precio objetivo


def evaluate(
    product: db.Product, current_price: float, in_stock: bool, db_path=None, currency: str = "COP"
) -> PriceVerdict:
    """Reglas, en orden:
    1. Sin stock -> nunca avisa.
    2. Volvió a tener stock (el chequeo anterior estaba agotado) -> avisa.
    3. Primer precio registrado -> no avisa (no hay contra qué comparar).
    4. Bajó menos que MIN_DROP_PERCENT (o no bajó) -> no avisa.
    5. Bajó, pero sigue en o arriba del mínimo de la ventana -> "descuento"
       de maquillaje, no avisa.
    6. Si no -> baja real, avisa.
    El precio objetivo se evalúa aparte, en checker.py.
    """
    history = db.price_history(product.id, db_path=db_path)
    # Último precio CON stock: los registros sin stock se guardan con precio 0,
    # y compararse contra eso cuando el producto vuelve rompe la detección.
    previous = next((p.price for p in reversed(history) if p.in_stock), None)

    min_window = db.min_price(product.id, config.FAKE_DISCOUNT_WINDOW_DAYS, db_path=db_path)
    all_time_low = min((p.price for p in history if p.in_stock), default=None)

    drop_percent = None
    if previous is not None and previous > 0:
        drop_percent = (previous - current_price) / previous * 100
    # Estricto: repetir el mismo precio NO es un "nuevo mínimo". Con `<=`,
    # un producto de precio estable mandaba un mail en cada chequeo.
    is_all_time_low = all_time_low is not None and current_price < all_time_low

    def verdict(should_alert: bool, reason: str, **extra) -> PriceVerdict:
        fields = dict(
            should_alert=should_alert,
            reason=reason,
            current_price=current_price,
            previous_price=previous,
            min_price_window=min_window,
            drop_percent=drop_percent,
            is_all_time_low=is_all_time_low,
        )
        fields.update(extra)
        return PriceVerdict(**fields)

    if not in_stock:
        return verdict(False, "Sin stock, no se evalúa el precio.", drop_percent=None, is_all_time_low=False)

    if history and not history[-1].in_stock:
        # Estaba agotado en el chequeo anterior y ahora hay stock: eso solo
        # ya vale un aviso (en Amazon pasa seguido y se vuelve a agotar rápido).
        return verdict(
            True, f"¡Volvió a estar en stock! Precio: {money.fmt(current_price, currency)}.", back_in_stock=True
        )

    if previous is None or drop_percent is None:
        return verdict(False, "Primer registro de precio.")

    if drop_percent < config.MIN_DROP_PERCENT:
        reason = "Sin baja de precio." if drop_percent <= 0 else (
            f"Bajó solo {drop_percent:.1f}%, por debajo del umbral de aviso."
        )
        return verdict(False, reason)

    # El chequeo clave contra el "descuento falso": no comparamos solo contra
    # el precio anterior (eso lo hace cualquier tienda con su cartelito de
    # "-30%"), comparamos contra el mínimo real de los últimos N días.
    if min_window is not None and current_price >= min_window:
        return verdict(
            False,
            f"Bajó {drop_percent:.1f}% desde el último chequeo, pero sigue en o por encima "
            f"del mínimo de los últimos {config.FAKE_DISCOUNT_WINDOW_DAYS} días "
            f"({money.fmt(min_window, currency)}). Probablemente el 'descuento' es maquillaje.",
            is_all_time_low=False,
        )

    if is_all_time_low:
        return verdict(True, "Nuevo mínimo histórico.")
    return verdict(True, f"Bajó {drop_percent:.1f}% y es un precio real (por debajo del mínimo reciente).")
