/*
 * Panel de pared con e-ink.
 *
 * Ciclo de vida (así es como dura meses con una sola batería):
 *   1. Despierta de deep sleep
 *   2. Prende WiFi, pide server/app.py -> panel.json
 *   3. Dibuja calendario + clima + tareas en la pantalla
 *   4. Apaga WiFi y vuelve a deep sleep por REFRESH_MINUTES
 *
 * Librerías necesarias (Arduino IDE: Sketch -> Include Library -> Manage
 * Libraries, o vía PlatformIO):
 *   - GxEPD2           (Jean-Marc Zingg)   -- driver de la pantalla e-ink
 *   - ArduinoJson (v7)                     -- parsear la respuesta del server
 *
 * Probado mentalmente contra una Waveshare 2.9" V2 (SSD1680, blanco y
 * negro). Si tu módulo es otro tamaño/driver, cambiá SOLO la sección
 * "PANTALLA" de más abajo — el resto del código no depende del modelo.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <esp_sleep.h>

#include <GxEPD2_BW.h>
#include <Fonts/FreeSans9pt7b.h>
#include <Fonts/FreeSans12pt7b.h>
#include <Fonts/FreeSansBold12pt7b.h>

#include "config.h"

// ---------------------------------------------------------------------
// PANTALLA — ajustá esto si tu módulo e-ink no es el que probamos.
// Pines por defecto para un ESP32 DevKit típico; cambialos si cableaste
// distinto (ver wall-panel/docs/wiring.md).
// ---------------------------------------------------------------------
#define EPD_CS    5
#define EPD_DC    17
#define EPD_RST   16
#define EPD_BUSY  4

GxEPD2_BW<GxEPD2_290_T94, GxEPD2_290_T94::HEIGHT> display(
    GxEPD2_290_T94(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

// ---------------------------------------------------------------------

RTC_DATA_ATTR int bootCount = 0;  // sobrevive el deep sleep, solo para debug

bool connectWiFi(uint32_t timeoutMs = 15000) {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < timeoutMs) {
    delay(250);
  }
  return WiFi.status() == WL_CONNECTED;
}

// Devuelve true si pudo traer y parsear el JSON. `doc` queda con los datos.
bool fetchPanelData(JsonDocument &doc) {
  HTTPClient http;
  http.begin(PANEL_API_URL);
  http.addHeader("X-Panel-Token", PANEL_TOKEN);
  http.setTimeout(10000);

  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    Serial.printf("GET falló, código HTTP: %d\n", code);
    http.end();
    return false;
  }

  DeserializationError err = deserializeJson(doc, http.getStream());
  http.end();

  if (err) {
    Serial.printf("Error parseando JSON: %s\n", err.c_str());
    return false;
  }
  return true;
}

void drawErrorScreen(const char *message) {
  display.setFullWindow();
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    display.setTextColor(GxEPD_BLACK);
    display.setFont(&FreeSans9pt7b);
    display.setCursor(10, 30);
    display.print("No pude actualizar:");
    display.setCursor(10, 55);
    display.print(message);
  } while (display.nextPage());
}

void drawPanel(JsonDocument &doc) {
  const char *dateLabel = doc["date_label"] | "";
  const char *timeLabel = doc["time_label"] | "";

  JsonArray events = doc["events"].as<JsonArray>();
  JsonArray taskList = doc["tasks"].as<JsonArray>();
  JsonObject w = doc["weather"];

  display.setFullWindow();
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    display.setTextColor(GxEPD_BLACK);

    // --- Encabezado: fecha + hora ---
    display.setFont(&FreeSansBold12pt7b);
    display.setCursor(6, 22);
    display.print(dateLabel);

    display.setFont(&FreeSans9pt7b);
    int16_t x1, y1; uint16_t w1, h1;
    display.getTextBounds(timeLabel, 0, 0, &x1, &y1, &w1, &h1);
    display.setCursor(display.width() - w1 - 6, 20);
    display.print(timeLabel);

    display.drawFastHLine(0, 30, display.width(), GxEPD_BLACK);

    int y = 50;

    // --- Clima ---
    if (!w.isNull()) {
      display.setFont(&FreeSans12pt7b);
      display.setCursor(6, y);
      int tempC = w["temp_c"] | 0;
      int tempMin = w["temp_min"] | 0;
      int tempMax = w["temp_max"] | 0;
      char buf[48];
      snprintf(buf, sizeof(buf), "%d C  (%d / %d)", tempC, tempMin, tempMax);
      display.print(buf);

      int rainChance = w["rain_chance"] | 0;
      if (rainChance >= 30) {
        display.setFont(&FreeSans9pt7b);
        char rainBuf[24];
        snprintf(rainBuf, sizeof(rainBuf), "Lluvia %d%%", rainChance);
        display.getTextBounds(rainBuf, 0, 0, &x1, &y1, &w1, &h1);
        display.setCursor(display.width() - w1 - 6, y);
        display.print(rainBuf);
      }
      y += 26;
    }

    display.drawFastHLine(0, y, display.width(), GxEPD_BLACK);
    y += 20;

    // --- Eventos de hoy ---
    display.setFont(&FreeSans9pt7b);
    if (events.size() == 0) {
      display.setCursor(6, y);
      display.print("Sin eventos hoy");
      y += 20;
    } else {
      for (JsonObject ev : events) {
        const char *title = ev["title"] | "";
        const char *start = ev["start"] | "";

        char line[64];
        snprintf(line, sizeof(line), "%s  %s", start, title);
        display.setCursor(6, y);
        display.print(line);
        y += 20;

        if (y > display.height() - 40) break;  // no hay más espacio
      }
    }

    y += 6;
    display.drawFastHLine(0, y, display.width(), GxEPD_BLACK);
    y += 20;

    // --- Tareas pendientes ---
    for (JsonVariant t : taskList) {
      const char *text = t.as<const char *>();
      char line[64];
      snprintf(line, sizeof(line), "[ ] %s", text);
      display.setCursor(6, y);
      display.print(line);
      y += 20;

      if (y > display.height() - 10) break;
    }

  } while (display.nextPage());
}

void goToSleep() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  display.hibernate();  // baja el consumo del panel e-ink en reposo

  uint64_t sleepMicros = (uint64_t)REFRESH_MINUTES * 60ULL * 1000000ULL;
  esp_sleep_enable_timer_wakeup(sleepMicros);
  esp_deep_sleep_start();
}

void setup() {
  Serial.begin(115200);
  delay(100);
  bootCount++;
  Serial.printf("Boot #%d\n", bootCount);

  display.init(115200);

  if (!connectWiFi()) {
    Serial.println("No pude conectar al WiFi.");
    drawErrorScreen("sin WiFi");
    goToSleep();
    return;
  }

  JsonDocument doc;  // ArduinoJson v7: se autoajusta, no hace falta StaticJsonDocument
  if (!fetchPanelData(doc)) {
    drawErrorScreen("el servidor no respondió");
    goToSleep();
    return;
  }

  drawPanel(doc);
  goToSleep();
}

void loop() {
  // No se usa: todo el trabajo pasa en setup() antes de dormir.
}
