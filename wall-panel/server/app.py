"""Servidor que arma el JSON que el ESP32 pide cada vez que se despierta.

El firmware es deliberadamente tonto: solo dibuja lo que este endpoint le
manda. Toda la parte "inteligente" (leer el calendario, el clima, las
tareas) vive acá, donde es fácil de cambiar sin volver a flashear el micro.

Correr (desde wall-panel/): uvicorn server.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import FastAPI, Header, HTTPException

from . import calendar_source, config, tasks, weather

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wall-panel")

app = FastAPI(title="Wall Panel API")

# strftime("%A %d de %B") depende del locale del sistema operativo, y no hay
# garantía de que el servidor donde corra esto tenga es_CO.UTF-8 instalado
# (de hecho, casi nunca lo tiene por defecto). En vez de pelearnos con
# locales, mapeamos los nombres a mano — es menos elegante pero funciona
# siempre, en cualquier máquina, sin configuración extra.
_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _spanish_date_label(now: datetime) -> str:
    return f"{_DIAS[now.weekday()]} {now.day} de {_MESES[now.month - 1]}"


def _check_token(x_panel_token: str | None) -> None:
    if config.PANEL_TOKEN and x_panel_token != config.PANEL_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")


@app.get("/panel.json")
def panel_data(x_panel_token: str | None = Header(default=None)):
    """Todo lo que el panel necesita para dibujarse, en una sola llamada
    (el ESP32 duerme la mayor parte del tiempo — cuantas menos requests,
    menos batería gasta despierto con el WiFi prendido)."""
    _check_token(x_panel_token)

    now = datetime.now()
    payload = {
        "generated_at": now.isoformat(),
        "date_label": _spanish_date_label(now),
        "time_label": now.strftime("%H:%M"),
    }

    # Cada sección falla independiente: si el calendario está caído, igual
    # querés ver el clima y las tareas.
    try:
        events = calendar_source.fetch_today(config.CALENDAR_ICS_URL) if config.CALENDAR_ICS_URL else []
        payload["events"] = [
            {
                "title": e.title,
                "start": e.start.strftime("%H:%M") if not e.all_day else "Todo el día",
                "end": e.end.strftime("%H:%M") if not e.all_day else "",
                "location": e.location,
            }
            for e in events
        ]
    except Exception:  # noqa: BLE001
        log.exception("No se pudo leer el calendario")
        payload["events"] = []
        payload["events_error"] = True

    try:
        w = weather.fetch(config.LATITUDE, config.LONGITUDE)
        payload["weather"] = {
            "temp_c": round(w.temp_c),
            "feels_like_c": round(w.feels_like_c),
            "condition": w.condition,
            "temp_min": round(w.temp_min_today),
            "temp_max": round(w.temp_max_today),
            "rain_chance": w.chance_of_rain_today,
        }
    except Exception:  # noqa: BLE001
        log.exception("No se pudo leer el clima")
        payload["weather"] = None

    try:
        payload["tasks"] = [t.text for t in tasks.pending(config.TASKS_PATH)][:6]  # el panel es chico
    except Exception:  # noqa: BLE001
        log.exception("No se pudieron leer las tareas")
        payload["tasks"] = []

    return payload


@app.post("/tasks")
def add_task(text: str, x_panel_token: str | None = Header(default=None)):
    """Agregar una tarea rápido desde curl/un atajo, sin abrir nada."""
    _check_token(x_panel_token)
    tasks.add(text, config.TASKS_PATH)
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}
