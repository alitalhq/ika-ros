# Gemstone üzerinde doğrudan ROS 2 kurulumu

Bu profil Ubuntu 24.04 ARM64 üzerinde ROS 2 Jazzy'yi ana sisteme kurar.
Docker gerekmez. Varsayılan kullanıcı `gemstone`, depo yolu
`/home/gemstone/ika-ros` olarak alınmıştır.

## Kurulum

```bash
git clone https://github.com/Emirsw/ika-ros.git ~/ika-ros
cd ~/ika-ros
sudo -v
bash deploy/install-native.sh
```

Betik ROS 2 apt kaynağını, motor/IMU/web bağımlılıklarını ve SLAM Toolbox'ı
kurar. GPIO v2 bağlaması sistem Python'unu değiştirmeden
`~/ika-gpio-venv` ortamına kurulur. Üreticinin `sllidar_ros2` kaynağı
`src/sllidar_ros2` içine indirilir; tüm yerel paketler `colcon` ile derlenir.
Derleme, kartın belleğine uygun olarak iki iş ve sıralı paket derlemesi kullanır.

Minimal Gemstone imajında CP2102 USB adaptörü `lsusb` içinde görünmesine
rağmen `/dev/ttyUSB0` oluşmuyorsa betik çalışan kernel sürümüne ait
`kernel-module-cp210x-*` paketini T3 apt deposundan kurar. Kernel imajını
değiştirmez. Bu paket bulunamazsa kurulum durur; eşleşen USB seri sürücüsü
sağlanmalıdır.

## Çalıştırma

```bash
sudo bash ~/ika-ros/deploy/start-native.sh
```

Bu profil motor/enkoder, dahili IMU, EKF, USB lidar, SLAM ve web arayüzünü
açar. Çizgi sensörü ve Nav2 kapalıdır. Başlangıç modu `idle` olur.

Donanım dosyası `deploy/hardware-usb-lidar.yaml` olarak seçilir. Bu kartta
fiziksel pin 40 başka bağlantıda olduğundan çizgi sensörünün D7 çıkışı
fiziksel pin 12 / GPIO18'e ayrılmıştır. D2–D6 sırasıyla fiziksel
31, 35, 37, 36, 38 pinlerine gider. GPIO18 bu profilde lidar motor PWM'i
olarak kullanılamaz; `lidar_motor:=false` korunmalıdır. Sensörün çıkış türü
doğrulanana kadar çizgi okuma kapalı kalır. UART lidarın motor PWM'ini
kullanan standart `hardware.yaml` dosyası değiştirilmemiştir.

### Sensör girişlerini hareket vermeden kontrol etme

Takılı D1–D8 etiketli kartın RC, dijital veya analog çıkış türü henüz
kesinleşmemiştir. Profildeki `type: qtr_rc` kalıtılan yer tutucudur;
çıkış türünü doğrulamadan `line:=true` kullanmayın. Analog çıkışlı
varyantta ADC gerekir; GPIO'da bir seviye görmek tek başına uygunluğu
kanıtlamaz. Sensör VCC/IR bağlantıları 3.3 V, GND ortak olmalıdır.

`line:=false` durumunda yalnız GPIO girişlerini okuyarak test edin:

```bash
cd ~/ika-ros
sudo env PYTHONPATH="$HOME/ika-gpio-venv/lib/python3.12/site-packages:$PWD/src/ika_hal" \
  python3 deploy/check-line-inputs.py --seconds 30
```

Araç pinlere çıkış sürmez. Sensörün altına önce beyaz, sonra siyah yüzey
yaklaştırın; ham seviyeleri ve kanal başına geçiş sayısını kontrol edin.
Bu robotun ilk 120 saniyelik testinde altı kanal da yalnız `1` okudu ve
geçiş sayıları sıfır kaldı. Kullanıcı beyaz/siyah denemesini ve IR/VCC/GND
bağlantısını doğruladı. Bu sonuç sensörün çalıştığını doğrulamaz; kartın
diğer yüzünden çıkış devresi/tipi ve gerekirse gerilimler incelenmelidir.

USB lidarın varsayılan kalıcı aygıt yolu:

```text
/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0
```

Adaptörünüzün yolu farklıysa `ls -l /dev/serial/by-id/` ile bulun ve
`deploy/start-native.sh` içindeki `lidar_port` değerini değiştirin.
`lidar_motor:=false` seçilidir; lidar motorunu USB adaptörü kontrol eder.

Kartın Wi-Fi adresini `ip -4 addr show wlan0` ile öğrenip aynı ağdaki
tarayıcıdan `http://<kart-ip>:8000` adresini açın. ROS WebSocket portu
9090'dır. Harita paneli `/map` verisini gösterir; lidarın tek başına
`/scan` yayınlaması panelde harita oluşturmaz.

## Açılışta otomatik başlatma

Ön plandaki launch sürecini Ctrl+C ile durdurun. Daha önceki kurulumdan
geçici `ika-native` servisi varsa `sudo systemctl stop ika-native` ile
durdurun. Ardından:

```bash
cd ~/ika-ros
cp deploy/start-native.sh ~/ika-start-native.sh
sudo install -m 644 deploy/ika-native.service /etc/systemd/system/ika-native.service
sudo systemctl daemon-reload
sudo systemctl enable --now ika-native
```

Servis dosyası `gemstone` kullanıcısının yollarını kullanır; başka hesapta
`WorkingDirectory`, `ExecStart` ve başlatma betiğindeki yolları uyarlayın.
Servis donanım erişimi için root olarak çalışır. Kod deposunun ve başlatma
betiğinin yazma erişimini yalnız yetkili kişilerle sınırlandırın.

```bash
sudo systemctl status ika-native
sudo systemctl restart ika-native
sudo systemctl stop ika-native
sudo journalctl -u ika-native -f
```

Servis çalışırken ayrıca ikinci bir `ros2 launch` başlatmayın. Servis
yeniden başlatıldığında tarayıcıdaki sayfayı yenileyin veya Bağlan'a basın.
ROS günlükleri `/var/log/ika-native` altındadır. Bu servis profilinde
harita kaydetme dizini mevcut `~/ika_maps` ayarı nedeniyle `/root/ika_maps`
olarak çözülür.

## Bu robotta yapılan yön ve sürüş ayarları

- Aynalı sağ motor için `right.invert: true` ve geri bildirimiyle uyumlu
  olacak şekilde `right.enc_invert: true` ayarlandı. Kullanıcı fiziksel
  denemede ileri komutunun düz ileri götürdüğünü doğruladı. Kendi
  kablolamanızda [saha testi](saha-testi.md) ile yönleri kontrol edin.
- Manuel web kontrolünde sağ/solun fiziksel yönü için açısal komutun işareti
  ters çevrildi. Ekran düğmeleri, klavye ve gamepad ortak düzeltmeyi kullanır.
  Bu değişiklik yalnız web teleop girişindedir; Nav2 ve ROS kinematiği
  değiştirilmedi. Otonom sürüşten önce teker tarafları, TF ve IMU yaw işaretleri
  birlikte kalibre edilmelidir.
- Varsayılan ileri/geri hedefi 0.40 m/s, kaydırıcı üst sınırı 0.80 m/s'dir.
  Dönüş varsayılanı 1.20 rad/s'dir. 0.60 rad/s ayarı bu robotta motorları
  yerinden kaldıramadığı için yükseltildi.
- Lidar freni korunur: hareket yönünde 0.20 m ve altında durur; 0.20–0.45 m
  arasında çizgisel hız kısılır. Arkada engel varsa geri komutu da kesilir.
- Motor kalkış duty'si, maksimum fiziksel hız, teker geometrisi ve PID
  değerlerinin tam kalibrasyonu henüz yapılmadı.

## Doğrulananlar

Kartta ROS paketleri derlendi; motor/enkoder/GPIO/mod yönetimine ait 36
birim testi geçti. GPIO/PWM pinleri çakışmasız çözüldü. Canlı kontrolde IMU,
odometri ve lidar verisi alındı; lidar yaklaşık 6.8 Hz'de 1080 nokta/tarama
üretti. SLAM haritası, `map` → `lidar_link` dönüşümü ve webde haritanın
çizilmesi doğrulandı. Kalıcı servis `enabled` ve `active` olarak doğrulandı;
servis etkinleştirildikten sonra ayrıca reboot testi yapılmadı.
