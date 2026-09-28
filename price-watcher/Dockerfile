FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# El bot corre por polling: no necesita exponer ningún puerto.
CMD ["python", "-m", "pricewatcher.bot"]
