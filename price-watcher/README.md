# Vigilante de precios

Bot de Telegram que sigue productos de MercadoLibre y Steam, guarda el
historial de precios, y te avisa **solo cuando la baja es real** — no cuando
la tienda "sube para bajar" (comparamos contra el mínimo de los últimos 90
días, no contra el precio de ayer).

Corre gratis: el bot vive donde vos lo prendas (tu PC, un rincón de un
servidor), y el chequeo periódico corre en **GitHub Actions** cada 6 horas,
sin que tengas que tener nada prendido.

## Cómo funciona

```
Vos (Telegram) ──/watch url──► bot.py ──► guarda producto en SQLite
                                              │
GitHub Actions (cron, cada 6h) ──────────────┤
                                              ▼
                                    checker.py recorre productos
                                              │
                                   scrapers/{mercadolibre,steam}.py
                                              │
                                    analysis.py: ¿esto es baja real?
                                              │
                                   sí ──► notify.py (Telegram + gráfico)
```

Agregar una tienda nueva = un archivo en `pricewatcher/scrapers/` que
implemente `matches(url)` y `fetch(url)`. Nada más del sistema necesita
tocarse — mirá `mercadolibre.py` o `steam.py` como plantilla.

## Instalación

### 1. Crear el bot de Telegram

Hablá con [@BotFather](https://t.me/BotFather) en Telegram → `/newbot` →
te da un token.

### 2. Configurar

```bash
cd price-watcher
python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# editá .env y pegá tu TELEGRAM_BOT_TOKEN
```

### 3. Correr el bot y conseguir tu chat_id

```bash
python -m pricewatcher.bot
```

Andá a Telegram, hablale a tu bot, mandale `/start`. Te va a devolver tu
`chat_id` — copialo a `.env` en `TELEGRAM_CHAT_ID` (lo necesita el cron, que
no tiene una conversación activa para saber a quién escribirle).

### 4. Seguir un producto

```
/watch https://articulo.mercadolibre.com.co/MCO-123456-algo
/watch https://store.steampowered.com/app/570/Dota_2/ 50000
```

El segundo ejemplo tiene precio objetivo: avisa apenas llegue a $50.000,
sin importar el umbral de baja general.

Comandos: `/list`, `/history <id>`, `/unwatch <id>`.

## Chequeo automático con GitHub Actions (gratis, sin servidor)

El workflow ya está en `.github/workflows/check-prices.yml`, corre cada 6
horas. Solo falta:

1. En GitHub → tu repo → **Settings → Secrets and variables → Actions**,
   creá dos *repository secrets*:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2. Pusheá — el workflow también se puede disparar a mano desde la pestaña
   **Actions** (`workflow_dispatch`) para probarlo sin esperar 6 horas.
3. El workflow commitea `data/pricewatcher.db` de vuelta al repo después de
   cada corrida, así el historial no se pierde entre ejecuciones (los
   runners de GitHub Actions son efímeros).

⚠️ Si el repo es público, cualquiera puede ver ese `.db` (son solo precios,
nada sensible, pero tenelo en cuenta). Si te importa, poné el repo en
privado o cambiá el workflow para guardar la base en otro lado (un gist
privado, un bucket S3 gratis, etc.).

## Correr los tests

```bash
pip install pytest
pytest tests/ -v
```

Los tests no pegan a internet: prueban el parsing de URLs de cada tienda y
la lógica de "¿esta baja es un descuento real o maquillaje?" con datos
simulados.

## Estructura

```
price-watcher/
├── pricewatcher/
│   ├── config.py       # todo desde variables de entorno
│   ├── db.py            # SQLite: productos + historial de precios
│   ├── scrapers/
│   │   ├── base.py      # contrato común (matches/fetch)
│   │   ├── mercadolibre.py
│   │   └── steam.py
│   ├── analysis.py      # ¿vale la pena avisar? (detección de descuento falso)
│   ├── charts.py         # gráfico de precio con matplotlib
│   ├── notify.py         # envío por Telegram
│   ├── checker.py        # recorre todos los productos (lo llama el cron)
│   └── bot.py             # bot interactivo (/watch, /list, /history...)
├── scripts/run_check.py  # entrypoint del cron
└── tests/
```

## Límites conocidos (honesto, no vendo humo)

- **Rappi y sitios con anti-bot fuerte no están soportados.** Requieren
  sesión, geolocalización y tienen protecciones que no vale la pena pelear
  para un uso personal.
- Los scrapers de HTML (si agregás una tienda sin API pública) se rompen
  cuando la tienda cambia su página. Los de MercadoLibre y Steam usan APIs
  públicas estables, así que son los más confiables.
- La detección de "descuento falso" necesita historial: recién es útil
  después de que el producto lleva algunas semanas siendo chequeado.
