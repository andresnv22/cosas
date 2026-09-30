#!/bin/bash
# Instala en tu Mac la tarea automática que chequea los productos de Amazon.
#
# Por qué en la Mac: Amazon bloquea las IPs de los servidores de GitHub
# (devuelve captcha), pero no la conexión de tu casa. GitHub sigue
# chequeando MercadoLibre y Steam; esta tarea hace solo Amazon.
#
# Corre a las 00:17, 06:17, 12:17 y 18:17. Si la Mac estaba dormida a esa
# hora, launchd la corre apenas se despierta. También corre al instalarla.
#
# Uso (desde cualquier carpeta):   bash price-watcher/scripts/mac/install.sh
# Desinstalar:                     bash price-watcher/scripts/mac/uninstall.sh

set -euo pipefail

LABEL="com.pricewatcher.amazon"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/pricewatcher-amazon.log"

PW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # .../price-watcher
PY="$PW_DIR/.venv/bin/python"

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; exit 1; }

echo "Instalando el chequeo de Amazon desde: $PW_DIR"
echo

# --- 1. Chequeos previos -------------------------------------------------
[ "$(uname)" = "Darwin" ] || fail "Esto es para macOS (launchd)."
command -v git >/dev/null || fail "No encuentro git."

if [ ! -x "$PY" ]; then
  echo "  … no hay entorno virtual, lo creo"
  python3 -m venv "$PW_DIR/.venv"
fi
"$PY" -m pip install -q -r "$PW_DIR/requirements.txt" || fail "No pude instalar las dependencias."
ok "Dependencias instaladas"

[ -f "$PW_DIR/.env" ] || fail "Falta $PW_DIR/.env (copiá .env.example y completá SMTP_USER, SMTP_PASSWORD, EMAIL_TO)."
"$PY" - "$PW_DIR" <<'PYEOF' || fail "El .env no tiene SMTP_USER, SMTP_PASSWORD y EMAIL_TO completos."
import sys
sys.path.insert(0, sys.argv[1])
from pricewatcher import config
sys.exit(0 if (config.SMTP_USER and config.SMTP_PASSWORD and config.EMAIL_TO) else 1)
PYEOF
ok "Mail configurado en .env"

BRANCH="$(git -C "$PW_DIR" rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" != "HEAD" ] || fail "El repo está en 'detached HEAD'; hacé checkout de la rama primero."
# La tarea corre sin terminal: si git necesita pedir usuario/contraseña, falla.
# --dry-run prueba las credenciales sin subir nada.
GIT_TERMINAL_PROMPT=0 git -C "$PW_DIR" push --dry-run origin "HEAD:$BRANCH" >/dev/null 2>&1 \
  || fail "git no puede subir sin pedir contraseña. Hacé un 'git push' a mano una vez (queda guardado en el llavero) y volvé a correr esto."
ok "git puede subir a la rama $BRANCH sin pedir contraseña"

# --- 2. Generar el .plist (con plistlib: rutas con espacios, sin drama) --
mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
"$PY" - "$PLIST" "$LABEL" "$PY" "$PW_DIR" "$LOG" <<'PYEOF'
import plistlib, sys
plist_path, label, py, pw_dir, log = sys.argv[1:6]
plist = {
    "Label": label,
    "ProgramArguments": [py, f"{pw_dir}/scripts/run_check.py", "--git-sync"],
    "WorkingDirectory": pw_dir,
    "EnvironmentVariables": {
        "ONLY_STORES": "amazon",
        "PRICEWATCHER_DB": "data/pricewatcher.db",
        "GIT_TERMINAL_PROMPT": "0",
        # launchd arranca con un PATH mínimo: git de Xcode o de Homebrew.
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    },
    "StartCalendarInterval": [{"Hour": h, "Minute": 17} for h in (0, 6, 12, 18)],
    "RunAtLoad": True,
    "StandardOutPath": log,
    "StandardErrorPath": log,
}
with open(plist_path, "wb") as f:
    plistlib.dump(plist, f)
PYEOF
plutil -lint "$PLIST" >/dev/null || fail "El .plist generado no es válido."
ok "Tarea creada: $PLIST"

# --- 3. Cargarla (si ya estaba, la reemplaza) ----------------------------
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST" || fail "launchctl no pudo cargar la tarea."
ok "Tarea cargada; ya está corriendo el primer chequeo"

echo
echo "Listo. Comandos útiles:"
echo "  Ver qué hizo:        tail -f \"$LOG\""
echo "  Correrla ya:         launchctl kickstart -k gui/\$(id -u)/$LABEL"
echo "  Desinstalar:         bash \"$PW_DIR/scripts/mac/uninstall.sh\""
