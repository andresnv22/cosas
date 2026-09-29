"""Tests del scraper de Amazon sin pegarle a Amazon: el HTML de abajo
reproduce la estructura real de la página (verificada contra amazon.com),
recortada a lo que importa.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricewatcher import analysis, db, money  # noqa: E402
from pricewatcher.scrapers import ScraperError, amazon, find_scraper_for  # noqa: E402

# Caso real: Echo Dot. La caja de compra dice US$39.99, pero
# #corePriceDisplay_desktop_feature_div / #apex_desktop muestran el precio
# "de lista" tachado US$79.99. Tomar el equivocado = precio inventado.
ECHO_DOT_HTML = """
<span id="productTitle"> Amazon Echo Dot: parlante Alexa </span>
<div id="apex_desktop"><span class="a-price"><span class="a-offscreen"></span></span>
  <span class="a-price"><span class="a-offscreen">US$79.99</span></span></div>
<div id="corePriceDisplay_desktop_feature_div">
  <span class="a-offscreen"></span><span class="a-offscreen">US$79.99</span></div>
<div id="corePrice_feature_div"><span class="a-offscreen">US$39.99</span></div>
<div id="tp_price_block_total_price_ww"><span class="a-offscreen">US$39.99</span></div>
<div id="availability"><span>Disponible</span></div>
"""

UNAVAILABLE_HTML = """
<span id="productTitle">MacBook Pro 2023</span>
<div id="availability"><span>No disponible por el momento. No sabemos si este
producto volverá a estar disponible, ni cuándo.</span></div>
"""

NO_PRICE_AVAILABLE_HTML = """
<span id="productTitle">Zapatillas (elegí talla)</span>
<div id="availability"><span>Disponible</span></div>
"""

CAPTCHA_HTML = """
<html><head><title>Amazon.com</title></head><body>
<form method="get" action="/errors/validateCaptcha">
<h4>Type the characters you see in this image:</h4></form></body></html>
"""


def test_matches_amazon_domains_and_short_links():
    assert amazon.matches("https://www.amazon.com/dp/B09B8V1LZ3")
    assert amazon.matches("https://www.amazon.com.mx/dp/B09B8V1LZ3")
    assert amazon.matches("https://amazon.es/dp/B09B8V1LZ3")
    assert amazon.matches("https://amzn.to/3abcDEF")
    assert amazon.matches("https://a.co/d/abc123")
    assert not amazon.matches("https://articulo.mercadolibre.com.co/MCO-123")
    # que "amazon" aparezca en la ruta de otro sitio no alcanza
    assert not amazon.matches("https://example.com/amazon.com/dp/B09B8V1LZ3")


def test_find_scraper_dispatches_amazon():
    assert find_scraper_for("https://www.amazon.com/dp/B09B8V1LZ3") is amazon


@pytest.mark.parametrize(
    "url,asin",
    [
        ("https://www.amazon.com/dp/B09B8V1LZ3", "B09B8V1LZ3"),
        ("https://www.amazon.com/Echo-Dot/dp/B09B8V1LZ3/ref=sr_1_3?crid=X&keywords=echo", "B09B8V1LZ3"),
        ("https://www.amazon.com/gp/product/B07ZPKBL9V?th=1", "B07ZPKBL9V"),
        ("https://www.amazon.com/gp/aw/d/B07ZPKBL9V", "B07ZPKBL9V"),
        ("https://www.amazon.com/dp/b09b8v1lz3", "B09B8V1LZ3"),
        ("https://www.amazon.com/s?k=echo+dot", None),
    ],
)
def test_extract_asin(url, asin):
    assert amazon.extract_asin(url) == asin


@pytest.mark.parametrize(
    "text,expected",
    [
        ("US$39.99", 39.99),
        ("US$1,249.00", 1249.00),
        ("$ 39.99", 39.99),
        ("1.249,00 €", 1249.00),
        ("39,99 €", 39.99),
        ("R$ 1.299,90", 1299.90),
        ("¥1,980", 1980.0),
        ("£12", 12.0),
        ("", None),
        ("Ver opciones", None),
    ],
)
def test_parse_price_formats(text, expected):
    assert amazon.parse_price(text) == expected


def test_picks_buy_box_price_not_strikethrough_list_price():
    result = amazon.parse_product_page(ECHO_DOT_HTML, "USD")
    assert result.price == 39.99
    assert result.in_stock is True
    assert result.currency == "USD"
    assert result.title == "Amazon Echo Dot: parlante Alexa"


def test_unavailable_product_is_out_of_stock_not_error():
    result = amazon.parse_product_page(UNAVAILABLE_HTML, "USD")
    assert result.in_stock is False
    assert result.price == 0.0


def test_available_without_price_raises_clear_error():
    with pytest.raises(ScraperError, match="no mostró un precio"):
        amazon.parse_product_page(NO_PRICE_AVAILABLE_HTML, "USD")


def test_captcha_detection():
    assert amazon._is_captcha(200, CAPTCHA_HTML)
    assert amazon._is_captcha(503, "")
    assert not amazon._is_captcha(200, ECHO_DOT_HTML)


def test_tld_to_currency():
    assert amazon._CURRENCY_BY_TLD[amazon._tld("www.amazon.com.mx")] == "MXN"
    assert amazon._CURRENCY_BY_TLD[amazon._tld("www.amazon.es")] == "EUR"
    assert amazon._CURRENCY_BY_TLD[amazon._tld("www.amazon.com")] == "USD"


def test_money_format_keeps_cents_for_usd_not_for_cop():
    assert money.fmt(39.99, "USD") == "US$39.99"
    assert money.fmt(26000, "COP") == "$26,000"
    assert money.fmt(1249.5, "EUR") == "€1,249.50"


def test_back_in_stock_compares_against_last_in_stock_price(tmp_path):
    """Precio 100 -> sin stock (se guarda como 0) -> vuelve a 80.
    La baja real es 100 -> 80, no 0 -> 80."""
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    product = db.add_product(url="https://www.amazon.com/dp/B000000001", store="amazon", db_path=db_path)

    db.record_price(product.id, 100.0, currency="USD", in_stock=True, db_path=db_path)
    db.record_price(product.id, 0.0, currency="USD", in_stock=False, db_path=db_path)

    verdict = analysis.evaluate(product, current_price=80.0, in_stock=True, db_path=db_path, currency="USD")

    assert verdict.previous_price == 100.0
    assert verdict.drop_percent == pytest.approx(20.0)
    assert verdict.should_alert is True


def test_back_in_stock_alerts_with_its_own_subject(tmp_path):
    from pricewatcher import checker

    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    product = db.add_product(url="https://www.amazon.com/dp/B000000002", store="amazon", title="Consola", db_path=db_path)
    db.record_price(product.id, 0.0, currency="USD", in_stock=False, db_path=db_path)

    verdict = analysis.evaluate(product, current_price=499.0, in_stock=True, db_path=db_path, currency="USD")
    assert verdict.should_alert is True
    assert verdict.back_in_stock is True

    subject, body = checker._format_alert(product, verdict, "USD")
    assert "Volvió el stock" in subject
    assert "US$499.00" in body
    assert "mínimo histórico" not in body.lower()


def test_still_in_stock_is_not_back_in_stock(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    product = db.add_product(url="https://www.amazon.com/dp/B000000003", store="amazon", db_path=db_path)
    db.record_price(product.id, 100.0, currency="USD", in_stock=True, db_path=db_path)

    verdict = analysis.evaluate(product, current_price=100.0, in_stock=True, db_path=db_path, currency="USD")
    assert verdict.back_in_stock is False
    assert verdict.should_alert is False


@pytest.mark.parametrize(
    "target,price,in_stock,previous,expected",
    [
        (35.0, 34.0, True, 40.0, True),    # cruzó hacia abajo: avisa
        (35.0, 33.0, True, 34.0, False),   # ya estaba abajo: no repite (anti-spam)
        (35.0, 34.0, True, None, True),    # primer precio ya abajo del objetivo: avisa
        (35.0, 0.0, False, 40.0, False),   # sin stock (precio 0): nunca
        (35.0, 36.0, True, 40.0, False),   # bajó pero no alcanza
        (None, 1.0, True, 40.0, False),    # sin objetivo
    ],
)
def test_target_price_only_alerts_on_crossing(target, price, in_stock, previous, expected):
    from pricewatcher import checker

    assert checker._crossed_target(target, price, in_stock, previous) is expected


def test_stable_price_never_alerts(tmp_path):
    """Regresión: con `<=` en el mínimo histórico, repetir el mismo precio
    mandaba un mail en cada chequeo (4 por día, para siempre)."""
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    product = db.add_product(url="https://www.amazon.com/dp/B000000004", store="amazon", db_path=db_path)
    for _ in range(5):
        db.record_price(product.id, 39.99, currency="USD", db_path=db_path)

    verdict = analysis.evaluate(product, current_price=39.99, in_stock=True, db_path=db_path, currency="USD")
    assert verdict.should_alert is False
    assert verdict.is_all_time_low is False


def test_back_in_stock_at_higher_price_does_not_say_it_dropped(tmp_path):
    from pricewatcher import checker

    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    product = db.add_product(url="https://www.amazon.com/dp/B000000005", store="amazon", title="X", db_path=db_path)
    db.record_price(product.id, 100.0, currency="USD", in_stock=True, db_path=db_path)
    db.record_price(product.id, 0.0, currency="USD", in_stock=False, db_path=db_path)

    verdict = analysis.evaluate(product, current_price=120.0, in_stock=True, db_path=db_path, currency="USD")
    subject, body = checker._format_alert(product, verdict, "USD")

    assert verdict.back_in_stock is True
    assert "Bajó" not in body
    assert "Volvió el stock" in subject


def test_target_hit_has_its_own_subject(tmp_path):
    from pricewatcher import checker

    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    product = db.add_product(url="https://www.amazon.com/dp/B000000006", store="amazon", title="Y", db_path=db_path)
    db.record_price(product.id, 40.0, currency="USD", db_path=db_path)

    verdict = analysis.evaluate(product, current_price=39.5, in_stock=True, db_path=db_path, currency="USD")
    verdict.hit_target = True
    verdict.should_alert = True
    subject, _ = checker._format_alert(product, verdict, "USD")

    assert "precio objetivo" in subject
