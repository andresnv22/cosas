"""Tests de gitsync con repos git reales (un remoto 'bare' y dos clones que
hacen de "la Mac" y "GitHub Actions"), forzando choques de push de verdad.
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricewatcher import db, gitsync  # noqa: E402

DB_REL = "price-watcher/data/pricewatcher.db"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def clone(remote: Path, dest: Path) -> Path:
    git(remote.parent, "clone", "-q", str(remote), str(dest))
    git(dest, "config", "user.name", dest.name)
    git(dest, "config", "user.email", f"{dest.name}@test")
    git(dest, "config", "pull.rebase", "true")
    return dest


@pytest.fixture
def repos(tmp_path):
    """Remoto con una base que ya tiene un producto, y dos clones al día."""
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))

    seed = clone(remote, tmp_path / "seed")
    (seed / "README.md").write_text("hola\n")
    db_path = seed / DB_REL
    db.init_db(db_path)
    db.add_product(url="https://www.amazon.com/dp/B000000001", store="amazon", title="Echo", db_path=db_path)
    git(seed, "add", ".")
    git(seed, "commit", "-q", "-m", "inicial")
    git(seed, "push", "-q", "origin", "HEAD:main")

    mac = clone(remote, tmp_path / "mac")
    gha = clone(remote, tmp_path / "gha")
    return remote, mac, gha


def history_in_remote(remote: Path, tmp_path: Path, name: str = "check") -> list[float]:
    fresh = clone(remote, tmp_path / name)
    return sorted(p.price for p in db.price_history(1, db_path=fresh / DB_REL))


def test_syncable(repos, tmp_path):
    _, mac, _ = repos
    assert gitsync.syncable(mac / DB_REL)
    loose = tmp_path / "suelto" / "x.db"
    loose.parent.mkdir()
    assert not gitsync.syncable(loose)


def test_simple_push(repos, tmp_path):
    remote, mac, _ = repos
    mac_db = mac / DB_REL
    summary = gitsync.run_and_push(
        lambda: db.record_price(1, 39.99, currency="USD", db_path=mac_db), mac_db, "chore: mac [skip ci]"
    )
    assert "1 precio" in summary
    assert history_in_remote(remote, tmp_path) == [39.99]


def test_no_changes_does_not_commit(repos):
    _, mac, _ = repos
    before = git(mac, "rev-parse", "HEAD")
    assert gitsync.run_and_push(lambda: None, mac / DB_REL, "x") == "Sin cambios en la base."
    assert git(mac, "rev-parse", "HEAD") == before


def test_conflict_replays_rows_and_keeps_both_machines_data(repos, tmp_path):
    """La Mac chequea Amazon; MIENTRAS tanto GitHub sube su propio chequeo.
    El push de la Mac choca -> tiene que re-aplicar su precio encima, sin
    perder el de GitHub."""
    remote, mac, gha = repos
    mac_db, gha_db = mac / DB_REL, gha / DB_REL

    def mac_check():
        db.record_price(1, 39.99, currency="USD", db_path=mac_db)
        # GitHub sube en el medio del chequeo de la Mac:
        gitsync.run_and_push(lambda: db.record_price(1, 41.00, currency="USD", db_path=gha_db), gha_db, "gha")

    summary = gitsync.run_and_push(mac_check, mac_db, "mac")

    assert "choque" in summary
    assert history_in_remote(remote, tmp_path) == [39.99, 41.00]
    # Y la Mac quedó limpia y al día con el remoto.
    assert git(mac, "status", "--porcelain") == ""
    assert git(mac, "rev-parse", "HEAD") == git(mac, "rev-parse", "origin/main")


def test_conflict_preserves_users_other_uncommitted_work(repos, tmp_path):
    """En la Mac puede haber trabajo sin commitear: nunca se puede tocar."""
    _, mac, gha = repos
    mac_db, gha_db = mac / DB_REL, gha / DB_REL
    (mac / "README.md").write_text("cambio sin commitear\n")
    (mac / "notas.txt").write_text("archivo nuevo sin trackear\n")

    def mac_check():
        db.record_price(1, 39.99, currency="USD", db_path=mac_db)
        gitsync.run_and_push(lambda: db.record_price(1, 41.00, currency="USD", db_path=gha_db), gha_db, "gha")

    gitsync.run_and_push(mac_check, mac_db, "mac")

    assert (mac / "README.md").read_text() == "cambio sin commitear\n"
    assert (mac / "notas.txt").read_text() == "archivo nuevo sin trackear\n"
    # ...y ninguno de los dos se coló en un commit.
    assert "README.md" not in git(mac, "show", "--name-only", "HEAD")


def test_dirty_db_refuses_instead_of_breaking(repos):
    _, mac, _ = repos
    mac_db = mac / DB_REL
    db.record_price(1, 10.0, db_path=mac_db)  # cambio en la base sin subir

    with pytest.raises(gitsync.GitSyncError, match="cambios sin subir"):
        gitsync.run_and_push(lambda: None, mac_db, "x")


def test_mutation_conflict_reapplies_on_newest(repos, tmp_path):
    """Agregar un producto mientras el otro lado sube precios: el producto
    nuevo y los precios del otro lado tienen que quedar los dos."""
    remote, mac, gha = repos
    mac_db, gha_db = mac / DB_REL, gha / DB_REL

    calls = []

    def add_product():
        calls.append(1)
        db.add_product(url="https://www.amazon.com/dp/B000000002", store="amazon", db_path=mac_db)
        if len(calls) == 1:  # GitHub sube solo durante el primer intento
            gitsync.run_and_push(lambda: db.record_price(1, 41.00, currency="USD", db_path=gha_db), gha_db, "gha")

    gitsync.mutate_and_push(add_product, mac_db, "mac: seguir")
    assert len(calls) == 2  # chocó una vez y se re-aplicó

    fresh = clone(remote, tmp_path / "check")
    urls = {p.url for p in db.list_products(db_path=fresh / DB_REL)}
    assert "https://www.amazon.com/dp/B000000002" in urls
    assert [p.price for p in db.price_history(1, db_path=fresh / DB_REL)] == [41.00]
