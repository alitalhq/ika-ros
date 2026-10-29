# Deneyap çizgi sensörü yazılımı

`deneyap_line.ino` sensörün sekiz analog çıkışını A0–A7 üzerinden okur ve
milivoltları saniyede yaklaşık 50 kez Gemstone'a UART üzerinden gönderir.
Aynı JSON satırları USB seri monitörde de görülür. Motor kontrolü yapmaz;
siyah/beyaz kalibrasyonu Gemstone'da saklanır.

## Arduino IDE ile Mini v2'ye yükleme

1. Bağlantıları değiştirmeden önce gücü kapatın. Yükleme sırasında Gemstone'a
   giden TX/RX kablolarını çıkarın; Mini v2'yi veri taşıyan USB kablosuyla PC'ye bağlayın.
2. Arduino IDE tercihlerindeki ek kart yöneticisi URL'lerine
   `https://raw.githubusercontent.com/deneyapkart/deneyapkart-arduino-core/master/package_deneyapkart_index.json`
   ekleyin. Kart yöneticisinden **Deneyap Gelistirme Kartlari 2.1.1** kurun.
3. `deneyap_line` klasöründeki **deneyap_line.ino** dosyasını açın.
4. Kartı **Deneyap Mini v2**, **USB CDC On Boot: Enabled** seçin ve Mini'nin
   COM portunu seçerek **Yükle** düğmesine basın. Kart 1A v2 seçmeyin: Mini v2
   ESP32-S2, Kart 1A v2 ESP32-S3 kullanır; ikili dosyaları farklıdır.
5. Bağlanamıyorsa BUTTON/BOOT basılıyken RESET'e basıp bırakın, sonra BUTTON'ı
   bırakın. Bootloader'ın COM portu değişebilir; yeni portu seçip tekrar yükleyin.
6. Seri monitörü **115200 baud** açın. Beklenen çıktı:

   ```json
   {"ika_adc":1,"seq":123,"mv":[1200,1210,1220,1230,1240,1250,1260,1270]}
   ```

Örnekteki değerler temsili; siyah ve beyaz yüzeylerde gerçek değerler değişmelidir.
Yükleme sonrası yazılım başlamazsa RESET'e bir kez basın.

## Mini v2 bağlantıları

Kablo değişiminde iki kartın da gücünü kapatın. Sensördeki **3.3V köprüsü
kapalıysa VCC yalnız 3V3'e** bağlanır.

| Sensör | Mini v2 | GPIO |
|---|---|---|
| D1 | A0 | 7 |
| D2 | A1 | 8 |
| D3 | A2 | 9 |
| D4 | A3 | 10 |
| D5 | A4 | 11 |
| D6 | A5 | 12 |
| D7 | A6 | 13 |
| D8 | A7 | 16 |
| VCC ve IR | 3V3 | — |
| GND | GND | — |

| Mini v2 | Gemstone |
|---|---|
| TX / D1 (GPIO43) | Fiziksel pin 10, GPIO15, RX |
| RX / D0 (GPIO44) | Fiziksel pin 8, GPIO14, TX |
| GND | Fiziksel pin 6, GND |

Sensörün **D1–D8** çıkışları Mini'nin **A0–A7** girişlerine gider; Mini'nin
D1 pini burada sensör girişi değil, Gemstone'a giden UART TX pinidir.
Mini'yi USB girişinden besleyin. Bu firmware'in Gemstone veri yolu UART'tır;
USB kablosu tek başına mevcut `/dev/ttyS3` sürücüsüne veri iletmez.

Gemstone'da `type: serial`, `serial.port: /dev/ttyS3`, `serial.baudrate: 115200`
olmalı. Arayüzde **Çizgi sensörü kalibrasyonu → Kalibrasyonu başlat → Beyaz
hazır → Siyah hazır** adımlarını izleyin. Önce ham mV değerlerinin yüzeyle
değiştiğini kontrol edin; kalibrasyon kablo/pin hatasını düzeltemez.

## Arduino CLI

Mini v2 için doğrulanan derleme hedefi:

```sh
arduino-cli compile --fqbn deneyap:esp32:deneyapminiv2:CDCOnBoot=cdc,UploadMode=default firmware/deneyap_line
```

Kart 1A v2 de aynı kaynak kodu kullanabilir; **Deneyap Kart 1A v2** seçilerek
yeniden derlenmeli ve o kartın A0–A7/TX/RX etiketlerine göre bağlanmalıdır.
Pin tanımları kart paketinden gelir; GPIO numaralarını kaynakta elle değiştirmeyin.
