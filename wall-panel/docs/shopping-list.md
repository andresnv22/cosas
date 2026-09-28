# Lista de compras

| Parte | Dónde | Precio aprox (USD) |
|---|---|---|
| ESP32 DevKit (30 pines) | AliExpress | $4 |
| Pantalla e-ink 2.9" (SSD1680, blanco y negro, con módulo driver) | AliExpress: buscar "2.9 inch e-paper SSD1680" | $12-15 |
| Batería 18650 + portapilas | AliExpress | $3 |
| Módulo cargador TP4056 (con protección) | AliExpress | $1 |
| Cables dupont hembra-hembra | ya los tenés del kit base | — |

**Total: ~$20-23**

## Notas de compra

- Pedí explícitamente el driver **SSD1680** — es el que soporta el firmware
  tal cual está escrito. Si tu módulo trae otro driver (IL3897, UC8151,
  etc.), hay que cambiar la clase de GxEPD2 en `firmware/wall_panel/src/wall_panel.ino` (la
  librería lista todos los modelos soportados en su `GxEPD2_display_selection.h`
  de ejemplo — buscá el que coincida con la etiqueta de tu módulo).
- Si preferís una pantalla más grande (4.2"), el código funciona igual —
  solo cambiá la clase `GxEPD2_290_T94` por la que corresponda a ese modelo
  y ajustá las coordenadas Y si el layout te queda apretado.
- El TP4056 no es estrictamente necesario si vas a alimentar el ESP32 desde
  un cargador USB fijo en vez de batería — en ese caso te ahorrás $4 (batería
  + cargador) y te olvidás del punto de la autonomía.

## Consumo estimado y autonomía

- El ESP32 duerme casi todo el tiempo (deep sleep: ~10-150 µA) y solo
  despierta ~5-10 segundos cada `REFRESH_MINUTES` para conectar WiFi, pedir
  datos y refrescar la pantalla (el e-ink no gasta energía para *mantener*
  la imagen, solo para cambiarla).
- Con `REFRESH_MINUTES = 20` y una batería 18650 de 2500mAh, la autonomía
  estimada ronda los **2-4 meses** — depende mucho de la calidad del WiFi
  (si tarda en conectar, gasta más por ciclo).
- Si notás que se agota más rápido de lo esperado, el sospechoso número uno
  es el tiempo de conexión WiFi — revisá que el router no tenga un modo de
  ahorro de energía que demore el handshake.
