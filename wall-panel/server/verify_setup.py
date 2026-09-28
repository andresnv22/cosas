#!/usr/bin/env python3
"""Valida server/.env antes de flashear nada. Corré esto después de
completar CALENDAR_ICS_URL y PANEL_TOKEN.

Uso (desde wall-panel/): python server/verify_setup.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import calendar_source, config, weather  # noqa: E402

OK = "✅"
FAIL = "❌"
WARN = "⚠️ "


def check_calendar() -> bool:
    if not config.CALENDAR_ICS_URL:
        print(f"{WARN} CALENDAR_ICS_URL está vacío — el panel va a mostrar 'Sin eventos hoy' siempre")
        print("   Google Calendar → configuración del calendario → Integrar calendario")
        print("   → copiá la 'Dirección pública en formato iCal'")
        return False

    try:
        events = calendar_source.fetch_today(config.CALENDAR_ICS_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"{FAIL} No pude leer el calendario: {exc}")
        print("   Revisá que el link sea el de iCal público, no el de compartir normal")
        return False

    print(f"{OK} Calendario OK — {len(events)} evento(s) hoy")
    for e in events[:5]:
        label = "Todo el día" if e.all_day else e.start.strftime("%H:%M")
        print(f"   · {label} — {e.title}")
    return True


def check_weather() -> bool:
    try:
        w = weather.fetch(config.LATITUDE, config.LONGITUDE)
    except Exception as exc:  # noqa: BLE001
        print(f"{FAIL} No pude leer el clima: {exc}")
        return False

    print(f"{OK} Clima OK — {w.temp_c}°C, {w.condition} (lat={config.LATITUDE}, lon={config.LONGITUDE})")
    print("   Si esas coordenadas no son las tuyas, ajustá LATITUDE/LONGITUDE en .env")
    return True


def check_token() -> bool:
    if not config.PANEL_TOKEN:
        print(f"{WARN} PANEL_TOKEN está vacío — el endpoint queda abierto a cualquiera en internet")
        print("   Poné cualquier cadena random en .env y la misma en firmware/wall_panel/src/config.h")
        return False

    print(f"{OK} PANEL_TOKEN configurado")
    return True


def main() -> int:
    print("Verificando wall-panel/server/.env...\n")
    cal_ok = check_calendar()
    print()
    weather_ok = check_weather()
    print()
    token_ok = check_token()

    print()
    if cal_ok and weather_ok and token_ok:
        print(f"{OK} Todo listo. Levantá el server y flasheá el ESP32.")
        return 0
    else:
        print(f"{WARN} Hay pasos pendientes — el server igual funciona, pero con menos datos.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
