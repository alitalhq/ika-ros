# İKA ROS

T3 Gemstone O1 üzerinde çalışan, modüler, kit olarak dağıtılabilecek
diferansiyel sürüşlü İKA yazılımı. **Ubuntu 24.04 + ROS 2 Jazzy**
(doğrudan kurulum veya Docker).

- Enkoder geri beslemeli motor hız kontrolü (teker başına PI + ileri besleme)
- Teker odometrisi + Gemstone dahili IMU füzyonu (robot_localization EKF)
- RPLIDAR A1 (Gemstone UART'ına doğrudan bağlı) ile haritalama (slam_toolbox),
  kayıtlı haritada Nav2 ile hedefe gitme
- Pololu QTR-8RC (veya dijital IR) çizgi sensörü ile çizgi izleme
- Host'tan tarayıcıyla kontrol: manuel sürüş (klavye, ekran, gamepad), mod
  seçimi, acil durdurma, canlı harita, harita kaydetme, haritaya tıklayıp hedef verme
- Lidar tabanlı çarpışma freni, `/cmd_vel` zaman aşımı, teleop devralma

## Hızlı başlangıç

### Robot: doğrudan ROS 2 kurulumu

Gemstone üzerinde kullanılan USB lidar + SLAM profili ve açılışta otomatik
başlatma adımları: [doğrudan kurulum](docs/native-kurulum.md).

```bash
git clone https://github.com/Emirsw/ika-ros.git ~/ika-ros
cd ~/ika-ros
sudo -v
bash deploy/install-native.sh
sudo bash deploy/start-native.sh
```

### Robot (Gemstone)

```bash
git clone <repo> ~/ika-ros && cd ~/ika-ros
docker compose build
docker compose up -d                 # tam robot: lidar + SLAM + arayüz
docker compose logs -f
```

Host'ta aynı ağdan tarayıcıyla **`http://<gemstone-ip>:8000`** açın.

Pin bağlantıları [docs/donanim.md](docs/donanim.md), ayarlar
`src/ika_bringup/config/hardware.yaml`. İlk kurulumda PWM overlay'lerini açıp
[saha testi](docs/saha-testi.md) adımlarını sırayla izleyin.

### Donanımsız (laptop)

```bash
IKA_ARGS="backend:=mock" docker compose up
```

Motor ve enkoderler benzetilir; IMU ve lidar kapanır. Tarayıcıda
`http://localhost:8000`. macOS / Windows'taki Docker Desktop'ta host ağı
sınırlıdır: `compose.yaml`'da `network_mode: host` satırını
`ports: ["8000:8000", "9090:9090"]` ile değiştirin.

> **Aynı ağda birden fazla robot varsa** her robota farklı bir
> `ROS_DOMAIN_ID` verin (`ROS_DOMAIN_ID=12 docker compose up -d`). Aksi halde
> aynı isimli node'lar birbirine karışır: bir robotun Nav2'si diğerinin
> node'larını yönetmeye çalışır, komutlar yanlış robota gider.

### Host'ta ROS 2 ile (isteğe bağlı)

Host ile robot aynı ağda ve aynı `ROS_DOMAIN_ID` ile:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel/teleop
ros2 service call /ika/set_mode ika_interfaces/srv/SetMode "{mode: line}"
rviz2                                # /map, /scan, TF; "2D Goal Pose" -> nav modu
```

## Launch

```bash
ros2 launch ika_bringup robot.launch.py [argüman:=değer ...]
```

| Argüman | Varsayılan | |
|---|---|---|
| `backend` | `gpiod` | `mock`: donanımsız benzetim |
| `hardware` | `config/hardware.yaml` | başka bir pin dosyası |
| `imu` / `fusion` | `true` / `true` | `fusion:=false` → odom TF'i teker odometrisinden |
| `lidar` | `true` | |
| `lidar_port` | — | boşsa `hardware.yaml` (`/dev/ttyS3`); USB adaptör: `/dev/ttyUSB0` |
| `lidar_motor` | `true` | lidar motorunu Gemstone PWM'i sürer; USB adaptörde `false` |
| `line` | `true` | çizgi sensörü + izleyici |
| `slam` / `slam_mode` / `map` | `true` / `mapping` / — | `slam_mode:=localization map:=~/ika_maps/salon` |
| `nav` | `false` | Nav2 |
| `gcs` | `true` | rosbridge `:9090` + web `:8000` |

## Yapı

```
src/
  ika_interfaces/   mesaj ve servisler
  ika_description/  URDF + robot.yaml (geometri için tek kaynak)
  ika_hal/          GPIO / PWM katmanı (libgpiod v1/v2, ad ile pin çözme, mock)
  ika_base/         motor + enkoder + PID + odometri, hw_check aracı
  ika_imu/          ICM-20948 sürücüsü
  ika_line/         QTR-8RC / dijital çizgi sensörü, çizgi izleme, line_check aracı
  ika_control/      mod yöneticisi, acil durdurma, lidar freni
  ika_navigation/   slam_toolbox, Nav2, harita kaydetme
  ika_gcs/          tarayıcı arayüzü
  ika_bringup/      robot.launch.py, hardware.yaml, control.yaml, ekf.yaml
docs/
  donanim.md        pin haritası, bağlantılar, elektriksel uyarılar
  saha-testi.md     ilk kurulum ve kalibrasyon kontrol listesi
  mimari.md         node / topic / mod yapısı
```

## Geliştirme

```bash
# Konteyner içinde (kaynak ./src bağlı):
colcon build --symlink-install
colcon test && colcon test-result --verbose

# ROS'suz birim testleri (herhangi bir makinede):
PYTHONPATH=src/ika_hal:src/ika_base:src/ika_line:src/ika_control pytest src/*/test
python3 -m flake8 src
```

Üçüncü parti kaynak paketleri `ika.repos` içinde (`vcs import src < ika.repos`).

## Lisans

Apache-2.0. `ika_imu/src/icm20948.c` ve `include/icm20948.h`: T3 Foundation, Apache-2.0.
