# Donanım ve pin haritası

Tüm bağlantılar yazılımda tek dosyada:
[`src/ika_bringup/config/hardware.yaml`](../src/ika_bringup/config/hardware.yaml).
Pinler Gemstone hat adlarıyla (`"GPIO22"`), PWM'ler modül adlarıyla (`"ecap0"`)
yazılır; yazılım bunları karttaki hatlara kendisi çözer. Robotta ilk komut:

```bash
ros2 run ika_base hw_check pins --config <hardware.yaml>
```

## Bileşenler

| Bileşen | Bağlantı | Yazılım |
|---|---|---|
| T3 Gemstone O1 | — | Ubuntu 24.04 + ROS 2 Jazzy (Docker) |
| L298N + 2 × Waveshare DCGM-3865 (12 V, 1:42, 240 rpm) | IN1–IN4 (GPIO), ENA/ENB (PWM) | `ika_base` |
| Motor enkoderleri (hall, AB, 546 PPR çıkış milinde, dahili pull-up) | 4 × GPIO | `ika_base` |
| ICM-20948 IMU | kart üzerinde, SPI `/dev/spidev0.3` | `ika_imu` |
| RPLIDAR A1 | USB adaptör (varsayılan) **veya** UART `/dev/ttyS3` + motor PWM | `sllidar_ros2`, `ika_hal` |
| 8 kanallı çizgi sensörü ("8路寻线模块", QTR-8 benzeri, analog çıkış) | 8 × GPIO | `ika_line` |
| 3S Li-Po (11.1 V) | L298N +12V; tüm GND'ler ortak | — |

## 40 pin header

Fiziksel pin = kart üzerindeki numara. Motor ve enkoder satırları kablolama
şemasıyla birebir aynıdır; lidar ve çizgi sensörü satırları şemada olmayan eklerdir.

**Sol/sağ** robotun arkasından, çizgi sensörünün olduğu öne bakarak söylenir.
Şemadaki Motor 1 (L298N OUT1/OUT2) robotun **sağ**, Motor 2 (OUT3/OUT4) **sol**
tekeridir; `hardware.yaml`'daki `left` / `right` buna göredir. Motorlar başka
tarafa takılırsa kablo değil `left` ve `right` blokları (yön ayarlarıyla
birlikte) yer değiştirir; doğrulamak için `hw_check motors` önce `left`'i döndürür.

| Pin | Sinyal | Bağlantı | `hardware.yaml` |
|---|---|---|---|
| 1 | 3V3 | Motor 1 enkoder VCC | — |
| 2, 4 | 5V | Lidar V5 ve VMOTO (yalnız GPIO bağlantısı) | — |
| 6 | GND | ortak GND | — |
| 7 | GPIO4 | Motor 1 (sağ teker) enkoder C1 | `right.enc_a` |
| 8 | GPIO14 (UART1 TX) | Lidar RX (yalnız GPIO bağlantısı) | `lidar_manager_node.gpio.port: /dev/ttyS3` |
| 10 | GPIO15 (UART1 RX) | Lidar TX (yalnız GPIO bağlantısı) | 〃 |
| 11 | GPIO17 | L298N IN2 (sağ teker) | `right.in2` |
| 12 | GPIO18 (ecap2) | Lidar MOTOCTL (yalnız GPIO bağlantısı) | `lidar_manager_node.gpio.pwm: ecap2` |
| 13 | GPIO27 | Motor 2 (sol teker) enkoder C1 | `left.enc_a` |
| 15 | GPIO22 | L298N IN1 (sağ teker) | `right.in1` |
| 16 | GPIO23 | Motor 2 (sol teker) enkoder C2 | `left.enc_b` |
| 17 | 3V3 | Motor 2 enkoder VCC, çizgi sensörü VCC | — |
| 18 | GPIO24 | L298N IN3 (sol teker) | `left.in1` |
| 22 | GPIO25 | L298N IN4 (sol teker) | `left.in2` |
| 24 | GPIO8 | Çizgi D7 | `pins[6]` |
| 26 | GPIO7 | Çizgi D8 | `pins[7]` |
| 29 | GPIO5 | Motor 1 (sağ teker) enkoder C2 | `right.enc_b` |
| 31 | GPIO6 | Çizgi D2 | `pins[1]` |
| 32 | GPIO12 (ecap0) | L298N ENA (sağ teker) | `right.pwm: ecap0` |
| 33 | GPIO13 (epwm1 B) | L298N ENB (sol teker) | `left.pwm: epwm1:1` |
| 35 | GPIO19 | Çizgi D3 | `pins[2]` |
| 36 | GPIO16 | Çizgi D5 | `pins[4]` |
| 37 | GPIO26 | Çizgi D4 | `pins[3]` |
| 38 | GPIO20 | Çizgi D6 | `pins[5]` |
| 39 | GND | Çizgi sensörü GND | — |
| 40 | GPIO21 | Çizgi D1 | `line_sensor_node.pins[0]` |

### Çizgi sensörü

Kitteki sensör **"8路寻线模块 / 8 sensor lines follow"** etiketli 8 kanallı
kart (Pololu QTR-8 tasarımının klonu). Her kanal 10 kΩ ile VCC'ye çekili bir
fototransistör: beyaz zeminde çıkış ≈ 0 V, siyah çizgide ≈ VCC. Karşılaştırıcı
yoktur; Gemstone GPIO'su bunu eşikle dijital okur (`type: digital`, siyah = 1).
Kart zemine **3–6 mm** mesafede olmalı, 1 cm'nin üstünde okuma alamaz.

| Sensör | Gemstone |
|---|---|
| VCC | pin 17 (**3.3 V**) |
| GND | pin 39 |
| IR | boşta (LED'ler açık) |
| D1 … D8 | pin 40, 31, 35, 37, 36, 38, 24, 26 |

- Kartın üstündeki **"3.3V" pedini lehimle birleştirin.** Köprü açıkken LED'ler
  3.3 V'ta çok zayıf yanar ve her kanal "siyah" (1) okur.
- **Asla 5 V vermeyin:** köprü lehimliyken LED'ler aşırı akımla yanar; ayrıca
  çıkışlar VCC'ye çekili olduğu için 5 V Gemstone pinlerine zarar verir.
- D1–D8 kablosu takılı değilken giriş boşta kalır ve 1 okuyabilir: Gemstone
  pad'lerinde iç pull-up/down yazılımdan açılamıyor. "Hep 1" görülürse önce
  VCC/GND ve D kablolarını kontrol edin.
- D7/D8 için kullanılan GPIO8/GPIO7 (pin 24/26) SPI0 seçim pinleridir; Gemstone
  imajında GPIO modundadır (IMU kart içinde ayrı bir seçim hattı kullanır).
  Pin 12 GPIO lidar seçeneğine ayrılmıştır, çizgi sensörüne verilmez.

## Lidar bağlantısı: USB veya GPIO

İki yol vardır; arayüzdeki **Lidar** panelinden seçilir, seçim robotta
(`~/.ika/lidar_source`) saklanır. Varsayılan USB'dir.

**USB (varsayılan):** Lidarı kendi adaptör kartıyla Gemstone'un USB portuna
takın; başka kablo gerekmez. Port `/dev/serial/by-id/` altında kendiliğinden
bulunur, motoru adaptör sürer. Minimal Gemstone imajında CP210x USB-seri
sürücüsü eksik olabilir: `lsusb` adaptörü gösterip `/dev/ttyUSB0` oluşmuyorsa
T3 apt deposundan `sudo apt install kernel-module-cp210x-$(uname -r)` ile
kurup `sudo modprobe cp210x` çalıştırın.

**GPIO:** Adaptör olmadan lidarın 7 pinli kablosu doğrudan header'a bağlanır:

| Lidar | Gemstone |
|---|---|
| V5, VMOTO | pin 2, pin 4 (5V) |
| GND (ikisi) | herhangi bir GND |
| TX | pin 10 (GPIO15, UART RX) |
| RX | pin 8 (GPIO14, UART TX) |
| MOTOCTL | pin 12 (GPIO18, `ecap2` PWM) |

Bu yol için `ecap2` overlay'i açık olmalı ve `/dev/ttyS3` bulunmalıdır.
Motor PWM'i yalnızca GPIO seçiliyken sürülür.

## Overlay'ler (`/boot/uEnv.txt`)

PWM kanalları `overlays=` satırına eklenen overlay'lerle açılır
([T3 PWM belgesi](https://docs.t3gemstone.org/tr/boards/o1/peripherals/pwm.md)):

```
k3-am67a-t3-gem-o1-pwm-ecap0-gpio12     # ENA
k3-am67a-t3-gem-o1-pwm-ecap2-gpio18     # lidar motoru (yalnız GPIO lidar bağlantısı)
k3-am67a-t3-gem-o1-pwm-epwm1-gpio13     # ENB
```

Dosya uzantısı ve satır biçimi için kartta `ls /boot/overlays` ve mevcut
`uEnv.txt` örneğine bakın. Değişiklikten sonra yeniden başlatın.

**Açmayın**, açarsanız kullandığımız GPIO'ları başka işe alırlar:

| Overlay | Bozduğu |
|---|---|
| `uart-ttys6` | GPIO4 (enkoder), GPIO17 (IN2); ayrıca Bluetooth'u kapatır |
| `uart-ttys0` | GPIO24 (IN3), GPIO7 |
| `pwm-epwm0-gpio5`, `pwm-epwm0-gpio5-gpio14` | GPIO5 (enkoder); ikincisi lidar UART TX'ini de kapatır |
| `pwm-ecap1-gpio16` | GPIO16 (çizgi D5) |
| `pwm-epwm1-gpio6`, `pwm-epwm1-gpio6-gpio13` | GPIO6 (çizgi D2) |

Kontroller:

```bash
ls -l /sys/class/pwm/      # hw_check pins hangi çipin hangi modül olduğunu yazar
ls /dev/ttyS3              # lidar UART'ı
```

`pwmchipN` numaraları yüklü overlay sayısına göre kayar. Belgedeki tablo
"hepsi açık" durumu içindir. Bu yüzden yapılandırmada numara değil modül adı
(`ecap0`, `epwm1:1`) kullanılır. Eski robottaki "GPIO13 fanla çakışıyor"
hatası büyük olasılıkla bu kaymadan kaynaklanıyordu; fan ayrı bir modülde
(`pwmchip7`, epwm2). Aynı epwm modülünün iki kanalı (GPIO6 ve GPIO13) aynı
periyodu paylaşmak zorundadır. GPIO6'yı PWM olarak açmadığımız için ENB
istediği periyodu alır; çakışma olursa sürücü kardeş kanalın periyoduna uyar
ve log'a uyarı yazar.

## Elektriksel uyarılar

- **Gemstone GPIO'ları 3.3 V'tur.** Enkoderler şemada 3V3'ten besleniyor;
  dahili pull-up'ları da 3.3 V'a çeker, doğru. 5 V'tan beslemeyin.
- **Çizgi sensörünü yalnızca 3.3 V ile besleyin** ve "3.3V" köprüsünü lehimleyin
  (yukarıda). IR boş kalabilir.
- Lidar 5 V ile beslenir ama UART sinyalleri 3.3 V'tur, doğrudan bağlanır.
  Lidar TX → Gemstone RX (pin 10), lidar RX → Gemstone TX (pin 8).
- L298N'de ENA/ENB jumper'ları **çıkarılmış** olmalı (şemadaki gibi).
- 3S pil dolu iken 12.6 V'tur; L298N ~2 V düşürür, motorlar anma geriliminin
  biraz altında çalışır. `max_wheel_speed`'i `hw_check sweep` ile ölçün.
- Batarya, L298N, Gemstone ve enkoder GND'leri ortak (şemadaki gibi).
