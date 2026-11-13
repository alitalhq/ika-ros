# İKA ROS

İKA ROS, T3 Gemstone O1 tabanlı, diferansiyel sürüşlü bir kara robotunun yazılımıdır. Robot üzerinde **Ubuntu 24.04 ve ROS 2 Jazzy** çalışır. Aynı ağdaki bir bilgisayardan tarayıcıyla robotu sürebilir, harita çıkarabilir ve çizgi sensörünü kalibre edebilirsiniz.

- **Manuel sürüş** — Klavye, ekrandaki yön tuşları veya gamepad ile kontrol. Tekerlek hızı enkoderlerle ölçülür, odometri kart üzerindeki IMU ile birleştirilir.
- **Çizgi izleme** — Sekiz kanallı analog sensör Deneyap Mini v2 üzerinden okunur. Beyaz ve siyah zemin ölçümleri web arayüzünden kaydedilir.
- **Haritalama ve navigasyon** — RPLIDAR A1 ile harita çıkarılır ve kaydedilir. Nav2 etkinleştirildiğinde harita üzerinden hedef verilebilir.

## Kurulum

### Gemstone O1 üzerinde

Ubuntu 24.04 yüklü Gemstone’da internet bağlantısı ve `sudo` yetkili bir kullanıcı gerekir. İlk çalıştırmadan önce [kablolamayı](#donanım-ve-pin-bağlantıları) kontrol edin, [pil ve kullanım güvenliği](docs/guvenlik.md) bölümünü okuyun ve [saha testi](docs/saha-testi.md) adımlarını izleyin.

```bash
git clone --branch codex/readme-donanim https://github.com/Emirsw/ika-ros.git ~/ika-ros
cd ~/ika-ros
bash deploy/install-native.sh
sudo bash deploy/start-native.sh
```

Kurulum betiği ROS 2 Jazzy’yi ve bağımlılıkları yükler, ardından çalışma alanını derler. Gemstone’da `hostname -I` ile ağ adresini bulun. Aynı ağa bağlı bilgisayarın tarayıcısında `http://<robot-ip>:8000` adresini açın. Robotu farklı bir kablosuz ağa bağlamak için [Wi-Fi kılavuzunu](docs/wifi.md) izleyin.

Robotu açılışta otomatik başlatmak için elle başlattığınız oturumu `Ctrl+C` ile durdurun ve depo dizininde şu komutu çalıştırın:

```bash
sudo bash deploy/install-service.sh 1
```

`1`, robotun `ROS_DOMAIN_ID` değeridir. Aynı ağdaki her robota farklı bir değer verin. Servis ayarları, günlükler ve güncelleme adımları [Docker’sız kurulum kılavuzunda](docs/native-kurulum.md) yer alır.

<details>
<summary>Docker ile çalıştırma ve donanımsız deneme</summary>

Docker ve Compose kurulu Linux sisteminde, depo dizininden robotu başlatın:

```bash
ROS_DOMAIN_ID=1 docker compose up --build -d
docker compose logs -f
```

Donanımsız arayüz denemesi için aynı dizinde imajı oluşturup aşağıdaki komutları çalıştırın. `backend:=mock` motor ve enkoderleri benzetir. Tarayıcıda `http://localhost:8000` adresini açın.

```bash
docker compose build
docker run --rm -p 8000:8000 -p 9090:9090 ika-ros:jazzy ros2 launch ika_bringup robot.launch.py backend:=mock fusion:=false line:=false slam:=false
```

</details>

## Donanım ve pin bağlantıları

Robotun ana bileşenleri **T3 Gemstone O1**, **L298N** motor sürücüsü, enkoderli iki **Waveshare DCGM-3865** motor, **Deneyap Mini v2**, sekiz kanallı analog çizgi sensörü ve **RPLIDAR A1**’dir.

[![İKA robotunun kablolama şeması. Gemstone O1, L298N, motorlar, enkoderler, Deneyap Mini v2, çizgi sensörü ve lidar.](docs/kablolama.svg)](docs/kablolama.svg)

[Gemstone O1 40 pin yerleşimi](docs/img/pinout.svg) · [Kablolama tablosu ve donanım ayarları](docs/donanim.md) · [Yazılımdaki pin yapılandırması](src/ika_bringup/config/hardware.yaml)

Aşağıdaki pin numaraları Gemstone’un 40 pinli konnektöründeki **fiziksel numaralardır**. Sağ ve sol, robotun arkasından önüne doğru bakıldığında belirlenir.

| Bileşen | Gemstone bağlantısı |
| --- | --- |
| L298N, sağ motor | IN1 → 15, IN2 → 11, ENA → 32 |
| L298N, sol motor | IN3 → 37, IN4 → 22, ENB → 33 |
| Sağ enkoder | C1 → 7, C2 → 29, 3,3 V → 1 |
| Sol enkoder | C1 → 13, C2 → 16, 3,3 V → 17 |
| Deneyap Mini v2 | TX (D1) → 10, RX (D0) → 8, GND → 6. Veri hattı `/dev/ttyS3`, 115200 baud. Mini v2, Mikro USB üzerinden beslenir. |
| RPLIDAR A1, varsayılan | Kendi USB adaptörüyle Gemstone’a bağlanır. |
| RPLIDAR A1, doğrudan UART | TX → 26, RX → 18, MOTOCTL → 12. Veri hattı `/dev/ttyS0`. [Gerekli donanım ayarları](docs/donanim.md#lidar-bağlantısı-usb-veya-gpio). |

Çizgi sensörünün D1–D8 çıkışlarını sırasıyla **Mini v2’nin A0–A7** girişlerine bağlayın. Sensörü 3,3 V ile besleyin ve üzerindeki `3.3V` köprüsünü kontrol edin. Ortak GND ve PWM bağlantıları için tam şemayı izleyin.

## İlk kullanım

1. **Deneyap yazılımını yükleyin.** Arduino IDE’de kart olarak **Deneyap Mini v2** seçin. COM portu görünmüyorsa **BUT** basılıyken **RES** tuşuna basıp bırakın, sonra **BUT** tuşunu bırakın ve yeni portu kontrol edin. [Yükleme ve bağlantı adımları](firmware/deneyap_line/README.md)
2. **Çizgi sensörünü kalibre edin.** Web arayüzünde **Çizgi sensörü kalibrasyonu → Kalibrasyonu başlat** seçeneğini kullanın. Sensörü çalışma yüksekliğinde tutarak sekiz kanalın tamamını önce beyaz, ardından mat siyah yüzey üzerinde ölçün. Ölçümler kaydedilince **Çizgi izle** modunu deneyin.
3. **Haritayı oluşturun ve kaydedin.** Varsayılan başlangıçta SLAM açıktır. Robotu **Manuel** modda gezdirin ve **Harita kaydet** panelini kullanın. Kayıtlı haritada hedefe gitmek için `slam_mode:=localization`, uzantısız `map` yolu ve `nav:=true` ile başlatın. [Başlatma ve servis ayarları](docs/native-kurulum.md)

## Proje belgeleri

| Belge | İçerik |
| --- | --- |
| [Mimari](docs/mimari.md) | ROS 2 paketleri, konular ve sürüş modları |
| [Donanım](docs/donanim.md) | Pinler, PWM, UART seçenekleri ve sensör kalibrasyonu |
| [Saha testi](docs/saha-testi.md) | İlk çalıştırma, motor yönü ve enkoder kontrolleri |

## Lisans

[Apache-2.0](LICENSE). ICM-20948 sürücüsünün kaynak dosyaları T3 Foundation’a aittir ve Apache-2.0 lisansıyla dağıtılır.
