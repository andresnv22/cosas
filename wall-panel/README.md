# Panel de pared con e-ink

ESP32 + pantalla e-ink que muestra tu calendario del día, el clima y tus
tareas pendientes. Dura meses con una sola batería porque el e-ink no gasta
energía para mantener la imagen, y el ESP32 duerme entre actualizaciones.

El firmware **solo dibuja** — no sabe nada de calendarios ni de clima. Le
pide un JSON ya armado a un servidorcito (`server/`), que es el que hace
todo el trabajo de leer tu Google Calendar y consultar el clima. Esa
separación importa: cambiar qué se muestra o de dónde sale es tocar Python
en tu PC, no volver a flashear el micro cada vez.

```
ESP32 (dormido la mayor parte del tiempo)
   │  cada REFRESH_MINUTES:
   │  1. despierta, prende WiFi
   ▼
server/app.py  ──GET /panel.json──►  {fecha, clima, eventos, tareas}
   │                                          ▲
   ├── calendar_source.py ── tu Google Calendar (.ics público)
   ├── weather.py ── Open-Meteo (gratis, sin API key)
   └── tasks.py ── data/tasks.json
   │
   ▼
ESP32 dibuja en la pantalla e-ink y vuelve a deep sleep
```

## Lista de compras y cableado

- [`docs/shopping-list.md`](docs/shopping-list.md) — qué comprar y dónde (~$20-23)
- [`docs/wiring.md`](docs/wiring.md) — diagrama de conexión pin por pin

> 🐳 Si preferís Docker: completá `server/.env` (pasos de abajo) y desde la
> raíz del repo corré `docker compose up -d --build wall-panel-server` —
> queda escuchando en `http://localhost:8000/panel.json`. Detalle en el
> README raíz.

## 1. Levantar el servidor

Podés correrlo en tu PC (mientras esté prendida) o en cualquier rincón
gratis con salida a internet — no necesita mucho.

```bash
cd wall-panel/server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# editá .env: CALENDAR_ICS_URL, LATITUDE/LONGITUDE, PANEL_TOKEN
```

Conseguir tu `CALENDAR_ICS_URL`: en Google Calendar → configuración del
calendario que querés mostrar → "Integrar calendario" → copiá la
"Dirección pública en formato iCal" (tenés que hacer el calendario público,
o al menos esa dirección secreta — Google la genera para vos).

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Probá que funciona:

```bash
curl -H "X-Panel-Token: tu_token" http://localhost:8000/panel.json
```

Deberías ver un JSON con tus eventos de hoy, el clima y las tareas.

### Agregar tareas

```bash
curl -X POST "http://localhost:8000/tasks?text=Comprar%20pan" -H "X-Panel-Token: tu_token"
```

O directamente editá `server/data/tasks.json` a mano.

## 2. Armar el hardware

Seguí [`docs/wiring.md`](docs/wiring.md). Antes de pegar todo con silicona,
probalo solo con cables dupont — es mucho más fácil corregir un pin mal
puesto así que después de armado.

## 3. Flashear el ESP32

Se usa **PlatformIO** (no Arduino IDE): instala las librerías exactas
automáticamente, y este firmware ya está **compilado y verificado** con este
método — `pio run` da `[SUCCESS]` con RAM al 16% y Flash al 73%, así que si
te da un error distinto, es de tu configuración (cableado/librerías locales),
no del código.

```bash
pip install -U platformio

cd firmware/wall_panel
cp src/config.h.example src/config.h
# editá src/config.h: tu WiFi, y PANEL_API_URL apuntando a la IP local de tu
# PC (no "localhost" — el ESP32 es otro dispositivo en la red), con el mismo
# PANEL_TOKEN que pusiste en server/.env

pio run                       # compila (probalo antes de tocar hardware)
pio run --target upload       # compila y flashea por USB
pio device monitor            # ver los logs (115200 baudios)
```

Si preferís Arduino IDE igual: Boards Manager → soporte ESP32, después
Library Manager → instalá **GxEPD2** (1.6.x), **ArduinoJson** (7.x),
**Adafruit GFX Library** y **Adafruit BusIO** — son las versiones exactas
que `platformio.ini` fija y con las que se probó.

Abrí el monitor serie (115200 baudios) para ver los logs mientras conecta
al WiFi y pide los datos — es la forma más rápida de diagnosticar si algo
falla antes de pasar a batería.

## Solución de problemas

| Síntoma | Causa probable |
|---|---|
| Pantalla en blanco, nada se dibuja | Cableado de `CS`/`DC`/`RST`/`BUSY` mal, o el driver de tu módulo no es SSD1680 |
| "sin WiFi" en la pantalla | Revisá `WIFI_SSID`/`WIFI_PASSWORD` en `config.h`; el ESP32 solo soporta redes de 2.4GHz, no 5GHz |
| "el servidor no respondió" | El server no está corriendo, la IP en `PANEL_API_URL` está mal, o el celular/PC y el ESP32 no están en la misma red |
| El panel no actualiza el calendario | El link `.ics` de Google Calendar puede tardar unos minutos en reflejar cambios nuevos — es así del lado de Google, no del código |
| Se agota la batería muy rápido | Ver la sección de autonomía en `docs/shopping-list.md` |

## Personalizar qué se muestra

Todo el layout se dibuja en `drawPanel()` dentro de
`firmware/wall_panel/src/wall_panel.ino`. Es dibujo directo con las funciones de
`Adafruit_GFX` (`setCursor`, `print`, `drawFastHLine`...) — no hay nada
mágico, es la forma más simple de tener control total del layout en una
pantalla tan chica.
