# Atajos para no tener que acordarte de los comandos largos.
# `make help` lista todo.

.PHONY: help setup-price-watcher setup-wall-panel test test-firmware up down logs

help:
	@echo "make setup-price-watcher   - venv + deps + copia .env.example -> .env"
	@echo "make setup-wall-panel      - venv + deps + copia .env.example -> .env"
	@echo "make test                  - corre los tests de price-watcher"
	@echo "make test-firmware         - compila el firmware del ESP32 (requiere PlatformIO)"
	@echo "make up                    - levanta todo con Docker Compose (requiere .env ya configurados)"
	@echo "make down                  - baja los contenedores"
	@echo "make logs                  - sigue los logs de los contenedores"

setup-price-watcher:
	cd price-watcher && python3 -m venv .venv && \
	.venv/bin/pip install -q -r requirements.txt && \
	test -f .env || cp .env.example .env
	@echo "Listo. Editá price-watcher/.env con tu TELEGRAM_BOT_TOKEN."

setup-wall-panel:
	cd wall-panel/server && python3 -m venv .venv && \
	.venv/bin/pip install -q -r requirements.txt && \
	test -f .env || cp .env.example .env
	@echo "Listo. Editá wall-panel/server/.env con tu CALENDAR_ICS_URL y PANEL_TOKEN."

test:
	cd price-watcher && python3 -m pytest tests/ -v

test-firmware:
	cd wall-panel/firmware/wall_panel && \
	test -f src/config.h || cp src/config.h.example src/config.h && \
	pio run

up:
	docker compose up -d --build
	@echo "price-watcher-bot corriendo en background."
	@echo "wall-panel-server en http://localhost:8000/panel.json"

down:
	docker compose down

logs:
	docker compose logs -f
