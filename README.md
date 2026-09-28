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

Cada carpeta tiene su propio README con la lista de compras, el diagrama de
conexión (para el panel) y las instrucciones de instalación.
