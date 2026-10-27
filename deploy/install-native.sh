#!/usr/bin/env bash
# Gemstone O1 (Ubuntu 24.04 ARM64) üzerine Docker'sız kurulum.
#   cd ~/ika-ros && bash deploy/install-native.sh
# Normal kullanıcıyla çalıştırın; sudo gereken adımlar şifre sorar.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$HOME/ika-gpio-venv"

echo '[1/5] ROS 2 apt kaynağı'
if ! dpkg-query -W -f='${Status}' ros2-apt-source 2>/dev/null | grep -q 'install ok installed'; then
  release=$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest)
  url=$(python3 -c 'import json, sys; d = json.load(sys.stdin); print(next(a["browser_download_url"] for a in d["assets"] if a["name"].endswith(".noble_all.deb")))' <<<"$release")
  curl -fsSL "$url" -o /tmp/ros2-apt-source.deb
  sudo dpkg -i /tmp/ros2-apt-source.deb
fi
# Gemstone imajında noble-updates yok; ROS paketleri ona göre derlenmiş.
if ! grep -RqsE '^deb .* noble-updates |^Suites:.*noble-updates' /etc/apt/sources.list /etc/apt/sources.list.d; then
  printf '%s\n' \
    'deb http://ports.ubuntu.com/ubuntu-ports noble-updates main universe multiverse' \
    'deb http://ports.ubuntu.com/ubuntu-ports noble-backports main universe multiverse' \
    'deb http://ports.ubuntu.com/ubuntu-ports noble-security main universe multiverse' \
    | sudo tee /etc/apt/sources.list.d/ika-ubuntu-updates.list >/dev/null
fi

echo '[2/5] ROS 2 Jazzy ve araçlar'
sudo apt-get update
sudo apt-get install -y --no-install-recommends ros-jazzy-ros-base python3-rosdep \
  python3-vcstool python3-colcon-common-extensions python3-venv python3-pip \
  build-essential cmake git curl

echo '[3/5] USB lidar sürücüsü (CP210x)'
# Minimal imajda modül yok: adaptör lsusb'de görünür ama /dev/ttyUSB0 oluşmaz.
if ! modinfo cp210x >/dev/null 2>&1; then
  driver="kernel-module-cp210x-$(uname -r)"
  if apt-cache show "$driver" >/dev/null 2>&1; then
    sudo apt-get install -y --no-install-recommends "$driver"
    sudo depmod -a
  else
    echo "UYARI: $driver bulunamadı; USB lidar çalışmaz (GPIO lidar bağlantısı etkilenmez)." >&2
  fi
fi
sudo modprobe cp210x 2>/dev/null || true

echo '[4/5] libgpiod v2 (ayrı Python ortamı)'
# apt'deki python3-libgpiod v1.6; enkoder okumak için v2'nin olay tamponu gerekir.
python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/pip" install --quiet 'gpiod>=2.2,<3'

echo '[5/5] Kaynaklar, bağımlılıklar ve derleme'
cd "$REPO"
[ -d src/sllidar_ros2 ] || vcs import src < ika.repos
[ -f /etc/ros/rosdep/sources.list.d/20-default.list ] || sudo rosdep init
rosdep update --rosdistro jazzy
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
set +u
source /opt/ros/jazzy/setup.bash
set -u
# Kartın belleği için sıralı derleme ve iki iş.
MAKEFLAGS=-j2 colcon build --symlink-install --executor sequential \
  --cmake-args -DBUILD_TESTING=OFF
echo
echo "Kurulum tamam. Denemek için:  sudo bash $REPO/deploy/start-native.sh"
echo "Açılışta başlatmak için:      sudo bash $REPO/deploy/install-service.sh <robot-no>"
