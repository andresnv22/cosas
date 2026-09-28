"""Lee los eventos de hoy desde un calendario público en formato ICS.

Funciona con cualquier calendario que tenga una URL .ics pública — en
Google Calendar: Configuración del calendario → "Integrar calendario" →
"Dirección pública en formato iCal". No hace falta OAuth ni credenciales.

Usa `recurring-ical-events` porque expandir eventos recurrentes (reuniones
semanales, etc.) a mano es más peliagudo de lo que parece — un evento
"todos los lunes" no aparece como tal en el ICS crudo, hay que calcularlo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

import httpx
import icalendar
import recurring_ical_events


@dataclass
class CalendarEvent:
    title: str
    start: datetime
    end: datetime
    all_day: bool
    location: str | None


def _to_datetime(value, end_of_day: bool = False) -> datetime:
    """Los eventos de día completo vienen como `date`, no `datetime`."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        t = time(23, 59) if end_of_day else time(0, 0)
        return datetime.combine(value, t)
    raise TypeError(f"Tipo de fecha inesperado en el ICS: {type(value)}")


def fetch_today(ics_url: str, timeout: float = 15.0) -> list[CalendarEvent]:
    resp = httpx.get(ics_url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()

    calendar = icalendar.Calendar.from_ical(resp.text)
    today = date.today()

    occurrences = recurring_ical_events.of(calendar).at(today)

    events = []
    for component in occurrences:
        start_raw = component.get("dtstart").dt
        end_raw = component.get("dtend").dt if component.get("dtend") else start_raw
        all_day = not isinstance(start_raw, datetime)

        events.append(
            CalendarEvent(
                title=str(component.get("summary", "(sin título)")),
                start=_to_datetime(start_raw),
                end=_to_datetime(end_raw, end_of_day=all_day),
                all_day=all_day,
                location=str(component.get("location")) if component.get("location") else None,
            )
        )

    events.sort(key=lambda e: (not e.all_day, e.start))
    return events
