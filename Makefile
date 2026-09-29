# Atajos para no tener que acordarte de los comandos largos.
# `make help` lista todo.

.PHONY: help setup-price-watcher setup-wall-panel verify-price-watcher verify-wall-panel watch list-products test test-firmware up down logs

help:
	@echo "make setup-price-watcher    - venv + deps + copia .env.example -> .env"
	@echo "make setup-wall-panel       - venv + deps + copia .env.example -> .env"
	@echo "make verify-price-watcher   - valida tu .env (SMTP) contra el servidor real, manda mail de prueba"
	@echo "make watch URL=<url>        - agrega un producto a seguir"
	@echo "make list-products          - lista lo que estás siguiendo"
	@echo "make verify-wall-panel      - valida tu .env (calendario/clima) contra las APIs reales"
	@echo "make test                   - corre los tests de price-watcher"
	@echo "make test-firmware          - compila el firmware del ESP32 (requiere PlatformIO)"
	@echo "make up                     - levanta todo con Docker Compose (requiere .env ya configurados)"
	@echo "make down                   - baja los contenedores"
	@echo "make logs                   - sigue los logs de los contenedores"

setup-price-watcher:
	cd price-watcher && python3 -m venv .venv && \
	.venv/bin/pip install -q -r requirements.txt && \
	test -f .env || cp .env.example .env
	@echo "Listo. Editá price-watcher/.env con tu SMTP_USER/SMTP_PASSWORD/EMAIL_TO."

setup-wall-panel:
	cd wall-panel/server && python3 -m venv .venv && \
	.venv/bin/pip install -q -r requirements.txt && \
	test -f .env || cp .env.example .env
	@echo "Listo. Editá wall-panel/server/.env con tu CALENDAR_ICS_URL y PANEL_TOKEN."

verify-price-watcher:
	cd price-watcher && .venv/bin/python scripts/verify_setup.py

watch:
	cd price-watcher && .venv/bin/python -m pricewatcher.cli watch $(URL) $(TARGET)

list-products:
	cd price-watcher && .venv/bin/python -m pricewatcher.cli list

verify-wall-panel:
	wall-panel/server/.venv/bin/python wall-panel/server/verify_setup.py

test:
	cd price-watcher && python3 -m pytest tests/ -v

test-firmware:
	cd wall-panel/firmware/wall_panel && \
	test -f src/config.h || cp src/config.h.example src/config.h && \
	pio run

up:
	docker compose up -d --build
	@echo "price-watcher-checker corriendo en background (chequeo cada 6h)."
	@echo "wall-panel-server en http://localhost:8000/panel.json"

down:
	docker compose down

logs:
	docker compose logs -f
