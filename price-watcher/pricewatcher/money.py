"""Formateo de precios según la moneda. COP no usa centavos en la práctica;
USD/EUR sí — mostrar US$39.99 como "$40" es mentir por redondeo."""

from __future__ import annotations

_ZERO_DECIMAL = {"COP", "CLP", "JPY", "KRW", "PYG"}

_PREFIX = {
    "COP": "$",
    "USD": "US$",
    "MXN": "MX$",
    "CAD": "CA$",
    "BRL": "R$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "INR": "₹",
    "AUD": "A$",
}


def fmt(amount: float, currency: str = "COP") -> str:
    currency = (currency or "COP").upper()
    number = f"{amount:,.0f}" if currency in _ZERO_DECIMAL else f"{amount:,.2f}"
    prefix = _PREFIX.get(currency, f"{currency} ")
    return f"{prefix}{number}"
