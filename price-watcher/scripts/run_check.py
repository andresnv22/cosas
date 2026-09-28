#!/usr/bin/env python3
"""Entrypoint para el cron / GitHub Actions. Solo llama al checker."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricewatcher.checker import run_all  # noqa: E402

if __name__ == "__main__":
    results = run_all()
    errors = [r for r in results if not r.ok]
    if errors:
        print(f"⚠️  {len(errors)} de {len(results)} productos tuvieron error.")
    # No hacemos sys.exit(1) por errores de scraping individuales: un sitio
    # caído no debería marcar todo el workflow de GH Actions como fallido.
