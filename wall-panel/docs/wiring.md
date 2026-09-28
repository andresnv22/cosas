# Conexionado

Pantalla e-ink 2.9" (SSD1680) ↔ ESP32 DevKit. Los pines de datos (`CS`,
`DC`, `RST`, `BUSY`) son configurables en `firmware/wall_panel/src/wall_panel.ino`
(constantes `EPD_CS`, `EPD_DC`, `EPD_RST`, `EPD_BUSY`) — si cableás distinto,
solo cambiá esos números, no hace falta tocar el resto del código.

| Pin de la pantalla | Pin del ESP32 | Notas |
|---|---|---|
| VCC | 3V3 | **No la alimentes con 5V** — el panel es de 3.3V |
| GND | GND | |
| DIN (MOSI) | GPIO 23 | SPI hardware por defecto del ESP32 |
| CLK (SCK) | GPIO 18 | SPI hardware por defecto |
| CS | GPIO 5 | configurable (`EPD_CS`) |
| DC | GPIO 17 | configurable (`EPD_DC`) |
| RST | GPIO 16 | configurable (`EPD_RST`) |
| BUSY | GPIO 4 | configurable (`EPD_BUSY`) |

```
        ESP32 DevKit                    Pantalla e-ink 2.9"
        ┌─────────────┐                 ┌─────────────────┐
   3V3  ●             │                 │  VCC             ●
   GND  ●             │                 │  GND             ●
GPIO23  ●─────────────┼─────────────────┼─ DIN             ●
GPIO18  ●─────────────┼─────────────────┼─ CLK             ●
 GPIO5  ●─────────────┼─────────────────┼─ CS              ●
GPIO17  ●─────────────┼─────────────────┼─ DC              ●
GPIO16  ●─────────────┼─────────────────┼─ RST             ●
 GPIO4  ●─────────────┼─────────────────┼─ BUSY            ●
        └─────────────┘                 └─────────────────┘
```

## Batería (opcional)

Si vas a alimentar con 18650 en vez de USB fijo:

```
18650(+) ── TP4056 (OUT+) ── ESP32 VIN
18650(-) ── TP4056 (OUT-) ── ESP32 GND
USB → TP4056 (IN)  (para cargar)
```

El TP4056 regula la carga de la batería; el ESP32 tiene su propio
regulador de 3.3V en la placa, así que conectás directo a `VIN` (5V) o a
`3V3` si tu módulo TP4056 ya entrega 3.3V regulados — revisá la etiqueta
del tuyo, varían.

⚠️ No conectes la batería directo al pin `3V3` sin pasar por un regulador:
una 18650 cargada da ~4.2V y eso frito el ESP32.

## Antes de armar todo junto

1. Conectá primero **solo la pantalla** (sin batería) y probá que el
   firmware la inicializa y dibuja algo (aunque sea el error de WiFi) —
   así aislás si el problema es de cableado o de código.
2. Después probá el WiFi y el pedido al server con el ESP32 todavía por
   USB, mirando el `Serial.println` en el monitor serie.
3. Recién ahí pasá a batería, cuando ya sabés que el resto funciona.
