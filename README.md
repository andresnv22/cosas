# cosas

Dos proyectos, cada uno en su carpeta, pensados para armarse rápido y quedar funcionando de verdad:

## [`price-watcher/`](price-watcher/) — Vigilante de precios

Bot de Telegram que sigue precios en MercadoLibre y Steam, guarda el historial,
y te avisa cuando algo baja de verdad (no cuando "suben para bajar"). Corre
gratis con GitHub Actions cada 6 horas — no necesita servidor propio.

**Empezar:** `cd price-watcher && cat README.md`

## [`wall-panel/`](wall-panel/) — Panel de pared con e-ink

ESP32 + pantalla e-ink que muestra tu calendario del día, el clima y tus
tareas, y dura meses con una sola batería. El firmware solo dibuja; un
servidorcito le manda los datos ya armados.

**Empezar:** `cd wall-panel && cat README.md`

---

## Arranque rápido con Docker

Una vez que tengas los `.env` completados en cada carpeta (mirá el README de
cada proyecto para conseguir los valores: token de Telegram, link de Google
Calendar, etc.), todo se levanta con:

```bash
docker compose up -d --build
```

Esto prende tres contenedores: el bot de Telegram, un chequeo de precios en
loop cada 6h (alternativa 100% self-hosted al cron de GitHub Actions), y el
server del panel en `http://localhost:8000/panel.json`. `docker compose logs -f`
para ver qué están haciendo, `docker compose down` para bajarlos.

También hay un `Makefile` con atajos (`make help` los lista) para no pelear
con los comandos largos de venv/pip/pytest.

## CI

- `.github/workflows/check-prices.yml` — corre el chequeo de precios cada 6h
- `.github/workflows/build-firmware.yml` — compila el firmware del ESP32 en
  cada push, para que un cambio roto se note en el PR y no cuando ya estás
  parado frente al panel con un cable USB en la mano

Cada carpeta tiene su propio README con la lista de compras, el diagrama de
conexión (para el panel) y las instrucciones de instalación.
