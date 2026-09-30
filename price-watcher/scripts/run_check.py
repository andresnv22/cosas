#!/usr/bin/env python3
"""Entrypoint del chequeo periódico.

    python scripts/run_check.py              # chequea y guarda en la base local
    python scripts/run_check.py --git-sync   # además trae lo último del repo antes,
                                             # y sube la base después (GitHub Actions,
                                             # la tarea programada de la Mac)

Qué tiendas se chequean lo definen ONLY_STORES / SKIP_STORES (ver config.py).
"""

import argparse
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricewatcher import config, gitsync  # noqa: E402
from pricewatcher.checker import run_all  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-sync", action="store_true", help="pull antes y push después, resolviendo choques")
    args = parser.parse_args()

    results: list = []

    def run():
        results.extend(run_all())

    if args.git_sync:
        if config.ONLY_STORES:
            stores = "solo " + ",".join(sorted(config.ONLY_STORES))
        elif config.SKIP_STORES:
            stores = "sin " + ",".join(sorted(config.SKIP_STORES))
        else:
            stores = "todas"
        message = f"chore: historial de precios ({stores}, {socket.gethostname()}) [skip ci]"
        try:
            print(gitsync.run_and_push(run, config.DB_PATH, message))
        except gitsync.GitSyncError as exc:
            print(f"❌ {exc}")
            return 1
    else:
        run()

    errors = [r for r in results if not r.ok]
    if errors:
        print(f"⚠️  {len(errors)} de {len(results)} productos tuvieron error.")
    # No devolvemos error por fallas de scraping individuales: un sitio
    # caído no debería marcar todo el chequeo como fallido.
    return 0


if __name__ == "__main__":
    sys.exit(main())
