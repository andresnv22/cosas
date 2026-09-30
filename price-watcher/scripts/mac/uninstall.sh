#!/bin/bash
# Saca la tarea automática de Amazon de tu Mac. No toca la base ni el repo.
set -euo pipefail

LABEL="com.pricewatcher.amazon"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null && echo "✓ Tarea detenida" || echo "· La tarea no estaba cargada"
if [ -f "$PLIST" ]; then
  rm "$PLIST"
  echo "✓ Borrado $PLIST"
fi
echo "Listo. El log sigue en ~/Library/Logs/pricewatcher-amazon.log por si lo querés revisar."
