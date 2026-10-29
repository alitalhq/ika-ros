// Deneyap Mini v2 / Kart 1A v2: 8 kanallı analog çizgi sensörü -> Gemstone.
//
// Sensör D1..D8 -> A0..A7. Arduino IDE'de FİZİKSEL kartı seçerek derleyin:
//   Mini v2 (ESP32-S2): GPIO 7, 8, 9, 10, 11, 12, 13, 16.
//   Kart 1A v2 (ESP32-S3): GPIO 4, 5, 6, 7, 15, 16, 17, 18.
// İki kartın derlenmiş .bin dosyaları birbirinin yerine kullanılamaz.
// Her ~20 ms'de bir satır:  {"ika_adc":1,"seq":<sayaç>,"mv":[D1,...,D8]}
//   UART0: TX GPIO43 -> Gemstone pin 10, RX GPIO44 <- pin 8, 115200 8N1.
//   Mini v2: TX=D1, RX=D0. Kart 1A v2: TX=D2, RX=D3.
//   USB CDC (hata ayıklama için aynı satırlar; bağlı değilse atlanır)
// Yükleme ve bağlantı: firmware/deneyap_line/README.md; docs/donanim.md.
//
// Arduino kart paketi: deneyap:esp32 2.1.1.
// Kart: "Deneyap Mini v2" VEYA "Deneyap Kart 1A v2" (elinizdeki modele göre).
// USB CDC On Boot: Enabled. Yüklemede kart açılmazsa BUTTON basılıyken
// RESET'e basıp bırakın, sonra BUTTON'ı bırakın.

#include <Arduino.h>

const uint8_t SENSOR_PINS[8] = {A0, A1, A2, A3, A4, A5, A6, A7};
const uint32_t BAUD = 115200;
const uint32_t PERIOD_MS = 20;  // 50 çerçeve/s
const int SAMPLES = 4;          // kanal başına ortalama

uint32_t sequence = 0;

void setup() {
  Serial.begin(BAUD);                         // USB CDC
  Serial0.begin(BAUD, SERIAL_8N1, RX, TX);    // UART0: GPIO44 RX, GPIO43 TX
  analogReadResolution(12);
  for (uint8_t pin : SENSOR_PINS) {
    pinMode(pin, INPUT);
    analogSetPinAttenuation(pin, ADC_11db);   // 0 .. ~3.1 V
  }
}

void loop() {
  uint32_t started = millis();
  uint32_t mv[8] = {};
  for (int round = 0; round < SAMPLES; ++round) {
    for (int ch = 0; ch < 8; ++ch) {
      mv[ch] += analogReadMilliVolts(SENSOR_PINS[ch]);
    }
  }
  char frame[128];
  int length = snprintf(frame, sizeof(frame),
      "{\"ika_adc\":1,\"seq\":%lu,\"mv\":[%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu]}\n",
      (unsigned long)sequence++,
      (unsigned long)(mv[0] / SAMPLES), (unsigned long)(mv[1] / SAMPLES),
      (unsigned long)(mv[2] / SAMPLES), (unsigned long)(mv[3] / SAMPLES),
      (unsigned long)(mv[4] / SAMPLES), (unsigned long)(mv[5] / SAMPLES),
      (unsigned long)(mv[6] / SAMPLES), (unsigned long)(mv[7] / SAMPLES));
  if (length > 0 && length < (int)sizeof(frame)) {
    Serial0.write((const uint8_t *)frame, length);
    if (Serial) {
      Serial.write((const uint8_t *)frame, length);
    }
  }
  uint32_t elapsed = millis() - started;
  if (elapsed < PERIOD_MS) {
    delay(PERIOD_MS - elapsed);
  }
}
