"""Capa de datos. SQLite: un solo archivo, cero configuración, alcanza de sobra
para un uso personal (algunas decenas de productos, chequeos cada 6 horas).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT NOT NULL UNIQUE,
    store         TEXT NOT NULL,          -- 'mercadolibre' | 'steam'
    title         TEXT,
    target_price  REAL,                   -- opcional: avisar solo por debajo de esto
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price         REAL NOT NULL,
    currency      TEXT NOT NULL DEFAULT 'COP',
    checked_at    TEXT NOT NULL,
    in_stock      INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_price_history_product
    ON price_history(product_id, checked_at);
"""


@dataclass
class Product:
    id: int
    url: str
    store: str
    title: Optional[str]
    target_price: Optional[float]
    active: bool
    created_at: str


@dataclass
class PricePoint:
    price: float
    currency: str
    checked_at: str
    in_stock: bool


def _row_to_product(row: sqlite3.Row) -> Product:
    return Product(
        id=row["id"],
        url=row["url"],
        store=row["store"],
        title=row["title"],
        target_price=row["target_price"],
        active=bool(row["active"]),
        created_at=row["created_at"],
    )


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def add_product(
    url: str,
    store: str,
    title: str | None = None,
    target_price: float | None = None,
    db_path: Path | None = None,
) -> Product:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO products (url, store, title, target_price, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET active = 1
            """,
            (url, store, title, target_price, datetime.utcnow().isoformat()),
        )
        # No confiamos en cur.lastrowid: en la rama ON CONFLICT DO UPDATE su
        # valor es None (no hubo INSERT nuevo), así que buscamos por la
        # columna única en vez de depender de esa semántica del driver.
        row = conn.execute("SELECT * FROM products WHERE url = ?", (url,)).fetchone()
        return _row_to_product(row)


def list_products(active_only: bool = True, db_path: Path | None = None) -> list[Product]:
    query = "SELECT * FROM products WHERE 1=1"
    if active_only:
        query += " AND active = 1"
    query += " ORDER BY created_at DESC"
    with connect(db_path) as conn:
        rows = conn.execute(query).fetchall()
        return [_row_to_product(r) for r in rows]


def get_product(product_id: int, db_path: Path | None = None) -> Optional[Product]:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return _row_to_product(row) if row else None


def deactivate_product(product_id: int, db_path: Path | None = None) -> bool:
    with connect(db_path) as conn:
        cur = conn.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))
        return cur.rowcount > 0


def set_title(product_id: int, title: str, db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute("UPDATE products SET title = ? WHERE id = ?", (title, product_id))


def record_price(
    product_id: int,
    price: float,
    currency: str = "COP",
    in_stock: bool = True,
    db_path: Path | None = None,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO price_history (product_id, price, currency, checked_at, in_stock)
            VALUES (?, ?, ?, ?, ?)
            """,
            (product_id, price, currency, datetime.utcnow().isoformat(), int(in_stock)),
        )


def price_history(product_id: int, days: int | None = None, db_path: Path | None = None) -> list[PricePoint]:
    query = "SELECT price, currency, checked_at, in_stock FROM price_history WHERE product_id = ?"
    params: list = [product_id]
    if days is not None:
        query += " AND checked_at >= datetime('now', ?)"
        params.append(f"-{days} days")
    query += " ORDER BY checked_at ASC"
    with connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [
            PricePoint(price=r["price"], currency=r["currency"], checked_at=r["checked_at"], in_stock=bool(r["in_stock"]))
            for r in rows
        ]


def last_price(product_id: int, db_path: Path | None = None) -> Optional[PricePoint]:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT price, currency, checked_at, in_stock FROM price_history
            WHERE product_id = ? ORDER BY checked_at DESC LIMIT 1
            """,
            (product_id,),
        ).fetchone()
        if not row:
            return None
        return PricePoint(price=row["price"], currency=row["currency"], checked_at=row["checked_at"], in_stock=bool(row["in_stock"]))


def min_price(product_id: int, days: int, db_path: Path | None = None) -> Optional[float]:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT MIN(price) as min_price FROM price_history
            WHERE product_id = ? AND checked_at >= datetime('now', ?) AND in_stock = 1
            """,
            (product_id, f"-{days} days"),
        ).fetchone()
        return row["min_price"] if row and row["min_price"] is not None else None
