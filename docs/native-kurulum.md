# Gemstone'a Docker'sız kurulum

ROS 2 Jazzy doğrudan karta kurulur, robot açılışta systemd servisiyle başlar.
Gemstone'da Docker sorun çıkarırsa bu yolu kullanın (Docker yolu için README).

Gereken: Gemstone Imager ile yazılmış **Ubuntu 24.04** imajı, internet, `sudo`
yetkili bir kullanıcı. Betikler kullanıcı adından ve repo yolundan bağımsızdır.

## 1. Kurulum

```bash
git clone https://github.com/alitalhq/ika-ros.git ~/ika-ros
cd ~/ika-ros
bash deploy/install-native.sh        # ~20-40 dk; sudo şifresi sorar
```

Betik sırasıyla:

1. ROS 2 apt kaynağını ve Ubuntu `noble-updates` deposunu ekler (Gemstone
   imajında yok; ROS paketleri ona göre derlenmiş).
2. `ros-jazzy-ros-base`, `rosdep`, `vcstool`, `colcon` kurar.
3. Lidarın USB adaptörü için **CP210x** sürücüsünü kurar. Minimal imajda yoktur:
   adaptör `lsusb`'de görünür ama `/dev/ttyUSB0` oluşmaz. Paket T3 apt
   deposundaki `kernel-module-cp210x-$(uname -r)`'dir; kernel değişmez.
4. Enkoder okumak için gereken libgpiod v2'yi sistem Python'una dokunmadan
   `~/ika-gpio-venv`'e kurar (apt'deki sürüm v1.6).
5. `ika.repos`'taki `sllidar_ros2`'yi indirir, `rosdep` ile tüm bağımlılıkları
   (slam_toolbox, Nav2, robot_localization, rosbridge, ...) kurar ve derler.

## 2. Deneme

```bash
sudo bash ~/ika-ros/deploy/start-native.sh
```

Aynı ağdaki bir tarayıcıdan `http://<kart-ip>:8000` açın (`hostname -I` IP'yi
verir). Lidar bağlantısı arayüzdeki **Lidar** panelinden seçilir (varsayılan
USB). Ctrl+C ile durdurun.

İlk kurulumda motor yönleri, enkoderler ve lidar için [saha testi](saha-testi.md)
adımlarını izleyin; `hw_check` komutlarının ortamı oradaki "Docker'sız kurulumda"
bölümündedir.

## 3. Açılışta otomatik başlatma

```bash
sudo bash ~/ika-ros/deploy/install-service.sh 1     # ikinci robotta: 2
```

Numara robotun `ROS_DOMAIN_ID`'sidir. **Aynı ağdaki her robota farklı numara
verin**; aynı numaradaki iki robotun node'ları birbirini görür ve bir robotun
arayüzünden verilen sürüş komutu diğerini de sürer. Arayüz her robotun kendi
IP'sinden açılır, numara arayüzü etkilemez.

Robot ayarları `/etc/default/ika`'dadır:

```bash
ROS_DOMAIN_ID=1
IKA_ARGS=""            # ör. "line:=false" ya da
                       # "slam_mode:=localization map:=~/ika_maps/salon nav:=true"
```

Değiştirdikten sonra `sudo systemctl restart ika`.

```bash
systemctl status ika
sudo systemctl restart ika
sudo systemctl stop ika              # elle start-native.sh çalıştırmadan önce
journalctl -u ika -f                 # canlı log
```

Servis çalışırken ikinci bir `ros2 launch` başlatmayın. Servis root olarak
çalıştığı için kaydedilen haritalar `/root/ika_maps`, lidar seçimi
`/root/.ika/lidar_source`, ROS logları `/var/log/ika` altındadır.

## Güncelleme

```bash
cd ~/ika-ros && git pull
source /opt/ros/jazzy/setup.bash
MAKEFLAGS=-j2 colcon build --symlink-install --executor sequential --cmake-args -DBUILD_TESTING=OFF
sudo systemctl restart ika
```

Yeni bağımlılık eklendiyse önce `rosdep install --from-paths src --ignore-src -y`.

## İki robot

Her kartta aynı adımlar; yalnızca `install-service.sh` numarası farklı
(1 ve 2). Kartları ayırt etmek için hostname'leri de değiştirin:
`sudo hostnamectl set-hostname ika1`.
