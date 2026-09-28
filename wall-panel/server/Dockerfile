FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# El resto del código de wall-panel/ se monta como volumen en docker-compose
# (server/ necesita verse como paquete junto al resto del repo para que los
# imports relativos `from . import ...` funcionen), pero para un build
# standalone también lo copiamos acá.
COPY . /app/server

EXPOSE 8000
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
