"""Tests que no pegan a internet: solo la lógica de parsing de URLs y la
detección de descuentos falsos. Correr con: pytest
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricewatcher.scrapers import mercadolibre, steam, find_scraper_for  # noqa: E402
from pricewatcher import analysis, db  # noqa: E402


def test_steam_matches():
    assert steam.matches("https://store.steampowered.com/app/570/Dota_2/")
    assert not steam.matches("https://www.mercadolibre.com.co/algo")


def test_steam_extract_appid():
    assert steam._extract_appid("https://store.steampowered.com/app/570/Dota_2/") == "570"


def test_mercadolibre_matches():
    assert mercadolibre.matches("https://articulo.mercadolibre.com.co/MCO-123456-cosa")


def test_mercadolibre_extract_item_id_full_url():
    url = "https://articulo.mercadolibre.com.co/MCO-1234567890-nombre-_JM"
    assert mercadolibre._extract_item_id_from_url(url) == "MCO1234567890"


def test_mercadolibre_extract_item_id_no_dash():
    url = "https://www.mercadolibre.com.co/nombre-producto/p/MCO12345678"
    assert mercadolibre._extract_item_id_from_url(url) == "MCO12345678"


def test_find_scraper_for_dispatches_correctly():
    assert find_scraper_for("https://store.steampowered.com/app/570/") is steam
    assert find_scraper_for("https://articulo.mercadolibre.com.co/MCO-1-x") is mercadolibre
    assert find_scraper_for("https://example.com/nada") is None


def test_fake_discount_is_not_alerted(tmp_path):
    """Simula: precio normal $100, 'oferta' a $70 (real), y después vuelve a
    $100 para inmediatamente 'bajar' a $85 — ese segundo descuento es falso
    porque $85 sigue arriba del mínimo real reciente ($70)."""
    db_path = tmp_path / "test.db"
    db.init_db(db_path)

    product = db.add_product(
        url="https://store.steampowered.com/app/1/test",
        store="steam",
        db_path=db_path,
    )

    db.record_price(product.id, 100.0, db_path=db_path)
    db.record_price(product.id, 70.0, db_path=db_path)  # baja real
    db.record_price(product.id, 100.0, db_path=db_path)  # vuelve a subir

    verdict = analysis.evaluate(product, current_price=85.0, in_stock=True, db_path=db_path)

    assert verdict.should_alert is False
    assert "descuento" in verdict.reason.lower() or "maquillaje" in verdict.reason.lower()


def test_real_new_low_is_alerted(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)

    product = db.add_product(
        url="https://store.steampowered.com/app/2/test",
        store="steam",
        db_path=db_path,
    )

    db.record_price(product.id, 100.0, db_path=db_path)
    db.record_price(product.id, 90.0, db_path=db_path)

    verdict = analysis.evaluate(product, current_price=60.0, in_stock=True, db_path=db_path)

    assert verdict.should_alert is True
    assert verdict.is_all_time_low is True
