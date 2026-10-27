# Mimari

## Paketler

| Paket | Tür | Görev |
|---|---|---|
| `ika_interfaces` | msg/srv | `LineState`, `SetMode`, `SaveMap` |
| `ika_description` | URDF | Robot modeli; geometri için tek kaynak `config/robot.yaml` |
| `ika_hal` | Python lib | GPIO (libgpiod v1/v2, hat adıyla çözme), sysfs PWM (modül adıyla), `mock`; `lidar_motor_node` |
| `ika_base` | Python | Enkoder geri beslemeli teker hız kontrolü, teker odometrisi, `hw_check` |
| `ika_imu` | C++ | ICM-20948 SPI sürücüsü, jiroskop sapma kalibrasyonu |
| `ika_line` | Python | QTR-8RC (RC zamanlama) veya dijital sensör dizisi, PD çizgi izleme, `line_check` |
| `ika_control` | Python | Mod yöneticisi: komut çoklayıcı, acil durdurma, lidar freni |
| `ika_navigation` | config + Python | slam_toolbox, Nav2, harita kaydetme servisi |
| `ika_gcs` | web + Python | Tarayıcı arayüzü, rosbridge, robot konumu yayını |
| `ika_bringup` | launch + config | Tek launch; tüm pinler `config/hardware.yaml` |

Donanımdan bağımsız mantık (kinematik, PID, enkoder çözme, çizgi konumu,
çoklayıcı, fren) ROS'suz modüllerdedir ve `pytest` ile test edilir.

## Veri akışı

```
              host (tarayıcı)  ──ws:9090──  rosbridge
                                               │
   /cmd_vel/teleop ─┐                          │  /ika/set_mode, /ika/estop,
   /cmd_vel/line  ──┼─▶ mode_manager_node ◀────┘  /ika/save_map, /goal_pose
   /cmd_vel/nav   ──┘     │  (mod + estop + lidar freni)
        ▲                 ▼
        │              /cmd_vel ──▶ ika_base_node ──▶ H-bridge PWM
        │                               │  ▲
   Nav2 ◀── /odometry/filtered ◀── EKF  │  └── enkoder (GPIO kenar olayları)
        ▲                          ▲    ▼
        │                          │  /wheel/odom, /joint_states
   slam_toolbox ◀── /scan          └── /imu/data_raw ◀── ika_imu_node
        │
      /map, map→odom TF

   line_sensor_node ──/line/state──▶ line_follower_node ──▶ /cmd_vel/line
```

## Modlar

| Mod | Motorlara ulaşan | Nasıl girilir |
|---|---|---|
| `idle` | hiçbiri | açılış, acil durdurma sonrası, arayüz |
| `manual` | `/cmd_vel/teleop` | arayüz, ya da herhangi bir modda sıfırdan farklı teleop (devralma) |
| `line` | `/cmd_vel/line` | arayüz |
| `nav` | `/cmd_vel/nav` | arayüzde haritaya tıklama veya `/goal_pose` |

Acil durdurma tüm modların önündedir ve mod `idle`'a düşer. `nav`'dan
çıkınca Nav2 hedefleri iptal edilir. Lidar freni her modda hareket
yönündeki engele göre ileri/geri hızı kısar (`control.yaml` → `safety`).

## TF ağacı

```
map ──(slam_toolbox)──▶ odom ──(EKF ya da fusion:=false ise ika_base_node)──▶ base_link
base_link ──▶ base_footprint, chassis_link, left/right_wheel_link,
              imu_link, lidar_link, line_sensor_link    (robot_state_publisher)
```

## Topic ve servisler

| İsim | Tip | Yayıncı |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | mode_manager_node |
| `/wheel/odom` | `nav_msgs/Odometry` | ika_base_node |
| `/ika_base_node/wheels` | `std_msgs/Float32MultiArray` | ika_base_node (PID ayarı için) |
| `/imu/data_raw` | `sensor_msgs/Imu` | ika_imu_node |
| `/odometry/filtered` | `nav_msgs/Odometry` | ekf_filter_node |
| `/scan` | `sensor_msgs/LaserScan` | sllidar_node |
| `/line/state` | `ika_interfaces/LineState` | line_sensor_node |
| `/line_follower/status` | `std_msgs/String` | line_follower_node |
| `/ika/mode` | `std_msgs/String` (latched) | mode_manager_node |
| `/ika/estop_active` | `std_msgs/Bool` (latched) | mode_manager_node |
| `/ika/obstacle_distance` | `std_msgs/Float32` | mode_manager_node |
| `/ika/robot_pose` | `geometry_msgs/PoseStamped` | robot_pose_node |
| `/ika/set_mode` | `ika_interfaces/SetMode` | mode_manager_node |
| `/ika/estop` | `std_srvs/SetBool` | mode_manager_node |
| `/ika/save_map` | `ika_interfaces/SaveMap` | map_manager_node |

## Eski repodan farklar

- Enkoderler artık zorunlu ve kapalı çevrim: teker başına ileri beslemeli PI.
  Eskisinde açık çevrim sürüş ve IMU tabanlı `motion_state` vardı.
- Odometri: rf2o (lazer odometrisi) ve Madgwick yerine robot_localization EKF
  (teker + jiroskop).
- Ultrasonik, kamera, Gazebo ve frontier keşfi çıkarıldı. Donanımsız deneme
  için `backend:=mock` var.
- `wheel_radius` / `wheel_separation` artık tek yerde (`robot.yaml`).
- GCS web arayüzü robotta çalışıyor; host'ta ROS kurulu olması gerekmiyor.
