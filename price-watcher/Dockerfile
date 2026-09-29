FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sin CMD fijo con sentido por defecto: este contenedor sirve tanto para el
# chequeo periódico (docker-compose.yml lo sobreescribe con un loop) como
# para correr el CLI puntualmente (`docker compose run --rm price-watcher-checker
# python -m pricewatcher.cli watch <url>`). Por default corre un chequeo único.
CMD ["python", "scripts/run_check.py"]
