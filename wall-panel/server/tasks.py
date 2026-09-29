"""Tareas del día: lo más simple que puede funcionar. Un archivo JSON que
editás a mano o con el par de funciones de acá. Si más adelante querés
cargarlas desde otro sistema (un CLI, un webhook, lo que sea), este módulo
es el único que hay que tocar — el resto del panel no sabe de dónde salen.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "tasks.json"


@dataclass
class Task:
    text: str
    done: bool = False


def load(path: Path = DEFAULT_PATH) -> list[Task]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Task(**t) for t in raw]


def save(tasks: list[Task], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(t) for t in tasks], ensure_ascii=False, indent=2), encoding="utf-8")


def add(text: str, path: Path = DEFAULT_PATH) -> None:
    tasks = load(path)
    tasks.append(Task(text=text))
    save(tasks, path)


def mark_done(index: int, path: Path = DEFAULT_PATH) -> None:
    tasks = load(path)
    if 0 <= index < len(tasks):
        tasks[index].done = True
        save(tasks, path)


def pending(path: Path = DEFAULT_PATH) -> list[Task]:
    return [t for t in load(path) if not t.done]
