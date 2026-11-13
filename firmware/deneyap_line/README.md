# Deneyap çizgi sensörü yazılımı

`deneyap_line.ino` sensörün sekiz analog çıkışını A0–A7 üzerinden okur ve
milivoltları saniyede yaklaşık 50 kez Gemstone'a UART üzerinden gönderir.
Aynı JSON satırları USB seri monitörde de görülür. Motor kontrolü yapmaz;
siyah/beyaz kalibrasyonu Gemstone'da saklanır.

## Deneyap Kart IDE ile Mini v2’ye yükleme

1. Bilgisayarınıza **Deneyap Kart IDE**’yi kurun. İlk açılışta **Geliştirme Ortamı
   Hazırlanıyor** ekranındaki indirmelerin tamamlanmasını bekleyin.
   [Deneyap Kart IDE kurulum kılavuzu](https://docs.deneyapkart.org/tr/IDE/Deneyap-Kart-IDE-Setup)
2. Bağlantıları değiştirmeden önce gücü kapatın. Yükleme sırasında Gemstone’a
   giden TX/RX kablolarını çıkarın ve Mini v2’yi veri aktarabilen bir Mikro USB kablosuyla bilgisayara bağlayın.
3. **Ayarlar → Dosya Aç** ile [`deneyap_line.ino`](deneyap_line.ino) dosyasını açın.
   Üst araç çubuğunda **Deneyap Mini v2** kartını seçin.
4. **Araçlar** menüsünde **Upload Mode** ayarını **Internal USB**, **USB CDC On
   Boot** ayarını **Enabled** yapın. Mini v2’nin portunu seçin ve **Derle ve
   Yükle**’ye tıklayın.
   [Deneyap Kart IDE arayüz kılavuzu](https://docs.deneyapkart.org/tr/IDE/Deneyap-Kart-IDE-Introduction)
5. Port görünmüyorsa **BUT** tuşunu basılı tutarken **RES** tuşuna basıp bırakın,
   ardından **BUT** tuşunu bırakın. **Portları Yenile** düğmesine tıklayın,
   yükleme modunda görünen portu seçip yeniden deneyin.
   [Deneyap Mini v2 sorun giderme kılavuzu](https://deneyapkart.org/docs/sorun-giderme-dymv2)
6. Yükleme tamamlanınca **Seri Monitör** sekmesinde kartın portunu ve
   **115200 baud** hızını seçip **Bağlan**’a tıklayın. Beklenen çıktı aşağıdaki
   gibi bir JSON satırıdır.

   ```json
   {"ika_adc":1,"seq":123,"mv":[1200,1210,1220,1230,1240,1250,1260,1270]}
   ```

Örnekteki değerler temsili; siyah ve beyaz yüzeylerde gerçek değerler değişmelidir.
Yükleme sonrası yazılım başlamazsa RESET'e bir kez basın.

## Mini v2 bağlantıları

Kabloları değiştirmeden önce iki kartın da gücünü kapatın. Sensörün
**VCC ucunu 3V3’e** bağlayın ve kart üzerindeki **3.3V** köprüsünü lehimleyin.

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
Mini v2’yi Mikro USB girişinden besleyin. Robot çalışırken ölçümler Gemstone’a
UART üzerinden iletilir.

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
