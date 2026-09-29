"""Tests del camino nuevo: CLI sin chat_id, parseo de destinatarios y
formato del mail. Nada de esto pega a un servidor SMTP real.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricewatcher import analysis, checker, config, db, notify  # noqa: E402


def test_add_product_no_longer_needs_chat_id(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)

    product = db.add_product(
        url="https://store.steampowered.com/app/99/x",
        store="steam",
        title="Juego X",
        db_path=db_path,
    )

    assert product.id is not None
    assert product.title == "Juego X"
    # Confirma que el dataclass Product ya no tiene chat_id
    assert not hasattr(product, "chat_id")


def test_unwatch_without_chat_id(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    product = db.add_product(url="https://store.steampowered.com/app/99/x", store="steam", db_path=db_path)

    assert db.deactivate_product(product.id, db_path=db_path) is True
    assert db.list_products(db_path=db_path) == []


def test_rewatch_updates_target_price(tmp_path):
    """Volver a seguir un producto con otro precio objetivo tiene que
    actualizarlo, no ignorarlo."""
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    url = "https://store.steampowered.com/app/99/x"

    db.add_product(url=url, store="steam", target_price=50000, db_path=db_path)
    product = db.add_product(url=url, store="steam", target_price=30000, db_path=db_path)

    assert product.target_price == 30000
    assert len(db.list_products(db_path=db_path)) == 1


def test_recipients_parses_comma_separated(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_TO", "a@x.com, b@y.com ,c@z.com")
    assert notify._recipients() == ["a@x.com", "b@y.com", "c@z.com"]


def test_recipients_empty_string(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_TO", "")
    assert notify._recipients() == []


def test_format_alert_has_subject_and_body(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    product = db.add_product(
        url="https://store.steampowered.com/app/99/x",
        store="steam",
        title="Juego con [corchetes] y guion_bajo",
        db_path=db_path,
    )
    db.record_price(product.id, 100.0, db_path=db_path)

    verdict = analysis.evaluate(product, current_price=60.0, in_stock=True, db_path=db_path)
    subject, body = checker._format_alert(product, verdict)

    assert "Juego con [corchetes] y guion_bajo" in subject or "Juego con [corchetes]" in subject
    assert "60" in body
    assert product.url in body


def test_send_alert_raises_clear_error_without_config(monkeypatch):
    monkeypatch.setattr(config, "SMTP_USER", "")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "")
    monkeypatch.setattr(config, "EMAIL_TO", "")

    try:
        notify.send_alert("asunto", "cuerpo")
        assert False, "debería haber lanzado RuntimeError"
    except RuntimeError as exc:
        assert "SMTP_USER" in str(exc) or "EMAIL_TO" in str(exc)
