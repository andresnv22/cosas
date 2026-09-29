# Vigilante de precios

Sigue productos de MercadoLibre y Steam, guarda el historial de precios, y
te avisa **por email, solo cuando la baja es real** — no cuando la tienda
"sube para bajar" (comparamos contra el mínimo de los últimos 90 días, no
contra el precio de ayer).

Vos agregás/sacás productos con un comando en tu PC (`pricewatcher.cli`);
el chequeo periódico corre solo en **GitHub Actions** cada 6 horas, sin que
tengas que tener nada prendido.

## Cómo funciona

```
Vos (tu PC) ──cli.py watch <url>──► guarda producto en SQLite
                                              │
GitHub Actions (cron, cada 6h) ──────────────┤
                                              ▼
                                    checker.py recorre productos
                                              │
                                   scrapers/{mercadolibre,steam}.py
                                              │
                                    analysis.py: ¿esto es baja real?
                                              │
                                   sí ──► notify.py (email + gráfico)
```

Agregar una tienda nueva = un archivo en `pricewatcher/scrapers/` que
implemente `matches(url)` y `fetch(url)`. Nada más del sistema necesita
tocarse — mirá `mercadolibre.py` o `steam.py` como plantilla.

> 🐳 Si preferís Docker: completá el `.env` (pasos de abajo) y desde la raíz
> del repo corré `docker compose up -d --build` — levanta el chequeo
> periódico sin tocar Python local. Detalle en el README raíz.

## Instalación

### 1. Conseguir credenciales SMTP

La forma más simple es con Gmail:

1. Activá verificación en 2 pasos en tu cuenta (si no la tenés)
2. Andá a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   y generá una "contraseña de aplicación" — **no** es tu contraseña normal,
   es una cadena de 16 caracteres solo para esto

Si usás otro proveedor de mail, necesitás su host/puerto SMTP (Outlook:
`smtp.office365.com:587`, tu propio dominio: preguntale a quien lo administra).

### 2. Configurar

```bash
cd price-watcher
python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# editá .env: SMTP_USER (tu mail), SMTP_PASSWORD (la contraseña de app), EMAIL_TO
```

Validá que quedó bien configurado — esto te manda un mail de prueba real:

```bash
python scripts/verify_setup.py
```

Si algo falla te dice exactamente qué (usuario/contraseña rechazados, host
inalcanzable, etc.) en vez de que te enteres cuando una alerta real no llegue.

### 3. Seguir un producto

```bash
python -m pricewatcher.cli watch https://articulo.mercadolibre.com.co/MCO-123456-algo
python -m pricewatcher.cli watch https://store.steampowered.com/app/570/Dota_2/ 50000
```

El segundo ejemplo tiene precio objetivo: avisa apenas llegue a $50.000,
sin importar el umbral de baja general.

Otros comandos:

```bash
python -m pricewatcher.cli list              # ver qué estás siguiendo
python -m pricewatcher.cli history <id>       # guarda el gráfico como PNG
python -m pricewatcher.cli unwatch <id>       # dejar de seguir
```

(O con `make`: `make watch URL=<url>`, `make list-products` — ver el
`Makefile` en la raíz.)

### Sin terminal: desde GitHub (o el celular)

El workflow **"Seguir producto"** (`.github/workflows/manage-products.yml`)
hace lo mismo que el CLI pero corre en GitHub: pestaña **Actions → Seguir
producto → Run workflow**, elegís la acción (`seguir` / `dejar_de_seguir` /
`listar`), pegás el link o el ID, y opcionalmente el precio objetivo.
Funciona igual desde la app de GitHub en el celular, y también se puede
disparar por API — así es como Claude lo maneja cuando le pedís "seguí este
artículo". Commitea la base actualizada solo, y nunca corre a la vez que el
chequeo periódico (comparten grupo de concurrencia), así que no se pisan.

## Chequeo automático con GitHub Actions (gratis, sin servidor)

El workflow ya está en `.github/workflows/check-prices.yml`, corre cada 6
horas. Solo falta:

1. En GitHub → tu repo → **Settings → Secrets and variables → Actions**,
   creá estos *repository secrets*:
   - `SMTP_HOST` (ej: `smtp.gmail.com`)
   - `SMTP_PORT` (ej: `587`)
   - `SMTP_USER`
   - `SMTP_PASSWORD`
   - `EMAIL_FROM` (puede ser igual a `SMTP_USER`)
   - `EMAIL_TO`
2. Pusheá — el workflow también se puede disparar a mano desde la pestaña
   **Actions** (`workflow_dispatch`) para probarlo sin esperar 6 horas.
3. El workflow commitea `data/pricewatcher.db` de vuelta al repo después de
   cada corrida, así el historial no se pierde entre ejecuciones (los
   runners de GitHub Actions son efímeros).

⚠️ Si el repo es público, cualquiera puede ver ese `.db` (son solo precios,
nada sensible, pero tenelo en cuenta). Si te importa, poné el repo en
privado o cambiá el workflow para guardar la base en otro lado (un gist
privado, un bucket S3 gratis, etc.).

Para agregar/sacar productos que sigue el chequeo automático, corré el CLI
localmente (apunta a la misma base que después se sube al repo) y pusheá el
cambio — o simplemente corré el CLI en tu PC con `PRICEWATCHER_DB` apuntando
a una copia del `data/pricewatcher.db` que bajaste del repo.

## Correr los tests

```bash
pip install pytest
pytest tests/ -v
```

14 tests, ninguno pega a internet: parsing de URLs de cada tienda, la
lógica de "¿esta baja es un descuento real o maquillaje?", y el armado del
mail (asunto/cuerpo, múltiples destinatarios) con datos simulados.

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
│   ├── notify.py         # envío por email (SMTP, sin dependencias nuevas)
│   ├── checker.py        # recorre todos los productos (lo llama el cron)
│   └── cli.py              # watch / list / unwatch / history, para uso local
├── scripts/
│   ├── run_check.py       # entrypoint del cron
│   └── verify_setup.py    # valida el .env contra el servidor SMTP real
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
- Sin comandos remotos: como las alertas van por email (no hay chat que
  conteste), agregar/sacar productos se hace corriendo el CLI en tu PC, no
  desde el celular. Si más adelante querés eso, un bot de Discord con
  comandos es la forma más simple de sumarlo sin tocar el resto del sistema.
