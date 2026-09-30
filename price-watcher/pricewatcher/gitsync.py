"""Corre el chequeo y sube la base al repo, resolviendo choques.

Dos máquinas escriben la misma base SQLite en git: GitHub Actions (Steam,
MercadoLibre) y la Mac del usuario (Amazon). Si las dos suben casi a la vez,
el segundo push se rechaza, y git no puede fusionar un archivo binario.

La solución: antes de chequear se anota el último id de `price_history`.
Si el push choca, se descartan los cambios locales SOLO de la base, se trae
la versión más nueva del remoto, y se re-insertan encima los registros que
agregó esta corrida. Así nunca se pierden los precios de la otra máquina ni
los propios, y no se re-mandan alertas (ya salieron en la primera pasada).

Nunca hace `reset --hard` ni toca otros archivos: en la Mac del usuario
puede haber trabajo sin commitear, y `--autostash` lo protege.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Callable

from . import db

log = logging.getLogger("gitsync")

MAX_PUSH_ATTEMPTS = 4


class GitSyncError(RuntimeError):
    pass


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise GitSyncError(f"git {' '.join(args)} falló: {result.stderr.strip() or result.stdout.strip()}")
    return result


def repo_root(start: Path) -> Path:
    return Path(_git(start, "rev-parse", "--show-toplevel").stdout.strip())


def current_branch(repo: Path) -> str:
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch == "HEAD":
        raise GitSyncError("El repo está en 'detached HEAD': no sé a qué rama subir la base.")
    return branch


def _pull(repo: Path, branch: str) -> None:
    _git(repo, "pull", "--rebase", "--autostash", "origin", branch)


def syncable(db_path: Path) -> bool:
    """¿La base vive en un repo git con remoto 'origin'? (en tests, Docker o
    una copia suelta no: ahí se trabaja solo con el archivo local)."""
    try:
        repo = repo_root(db_path.resolve().parent)
        _git(repo, "remote", "get-url", "origin")
        return True
    except (GitSyncError, FileNotFoundError, OSError):
        return False


def _prepare(db_path: Path) -> tuple[Path, str, str]:
    db_path = db_path.resolve()
    repo = repo_root(db_path.parent)
    branch = current_branch(repo)
    db_rel = str(db_path.relative_to(repo))
    if _git(repo, "status", "--porcelain", "--", db_rel).stdout.strip():
        raise GitSyncError(
            f"La base ({db_rel}) tiene cambios sin subir. Subilos (git add/commit/push) "
            "o descartalos (git checkout -- " + db_rel + ") y volvé a intentar."
        )
    return repo, branch, db_rel


def _commit_and_push(repo: Path, branch: str, db_rel: str, message: str) -> bool:
    _git(repo, "add", "--", db_rel)
    _git(repo, "commit", "-m", message, "--", db_rel)
    return _git(repo, "push", "origin", f"HEAD:{branch}", check=False).returncode == 0


def _drop_local_commit(repo: Path, branch: str, db_rel: str) -> None:
    """Deshace SOLO nuestro commit de la base y trae lo último del remoto."""
    _git(repo, "reset", "--soft", "HEAD~1")
    _git(repo, "restore", "--staged", "--", db_rel)
    if _git(repo, "checkout", "HEAD", "--", db_rel, check=False).returncode != 0:
        # La base no existía antes de nuestro commit: la saca y la trae el pull.
        (repo / db_rel).unlink(missing_ok=True)
    _pull(repo, branch)


def mutate_and_push(mutate: Callable[[], object], db_path: Path, message: str) -> None:
    """Para cambios de productos (watch/unwatch): trae lo último, aplica,
    sube. Si choca, vuelve a aplicar sobre la versión nueva — watch y unwatch
    son idempotentes, así que repetirlos es seguro."""
    repo, branch, db_rel = _prepare(db_path)
    _pull(repo, branch)
    mutate()

    for attempt in range(1, MAX_PUSH_ATTEMPTS + 1):
        if _git(repo, "status", "--porcelain", "--", db_rel).stdout.strip() == "":
            return
        if _commit_and_push(repo, branch, db_rel, message):
            return
        log.warning("El push chocó con cambios de otra máquina (intento %d), repito sobre lo nuevo", attempt)
        _drop_local_commit(repo, branch, db_rel)
        mutate()

    raise GitSyncError(f"No pude subir la base después de {MAX_PUSH_ATTEMPTS} intentos.")


def run_and_push(run: Callable[[], object], db_path: Path, message: str) -> str:
    """Trae lo último, ejecuta `run()` (el chequeo), y sube la base.

    Devuelve un resumen de lo que pasó. Lanza GitSyncError si no pudo subir
    después de varios intentos (lo raro: haría falta que la otra máquina
    suba justo en cada reintento).
    """
    repo, branch, db_rel = _prepare(db_path)
    db_path = db_path.resolve()

    _pull(repo, branch)
    db.init_db(db_path)
    start_id = db.max_history_id(db_path)

    run()

    new_rows = db.history_rows_since(start_id, db_path)
    if _git(repo, "status", "--porcelain", "--", db_rel).stdout.strip() == "":
        return "Sin cambios en la base."

    for attempt in range(1, MAX_PUSH_ATTEMPTS + 1):
        if _commit_and_push(repo, branch, db_rel, message):
            suffix = f" (tras {attempt - 1} choque/s)" if attempt > 1 else ""
            return f"Base subida: {len(new_rows)} precio/s nuevo/s{suffix}."

        log.warning("El push chocó con cambios de otra máquina (intento %d), re-aplico encima", attempt)
        _drop_local_commit(repo, branch, db_rel)
        inserted = db.insert_history_rows(new_rows, db_path)
        log.info("Re-apliqué %d de %d registros sobre la versión más nueva", inserted, len(new_rows))

    raise GitSyncError(f"No pude subir la base después de {MAX_PUSH_ATTEMPTS} intentos.")
