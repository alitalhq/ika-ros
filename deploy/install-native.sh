#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
echo '[1/4] ROS apt source'
if ! dpkg-query -W -f='${Status}' ros2-apt-source 2>/dev/null | grep -q 'install ok installed'; then
  curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest -o /tmp/ika-ros-apt-release.json
  source_url=$(python3 -c 'import json; d=json.load(open("/tmp/ika-ros-apt-release.json")); print(next(a["browser_download_url"] for a in d["assets"] if a["name"].endswith(".noble_all.deb")))')
  curl -fL "$source_url" -o /tmp/ika-ros2-apt-source.deb
  sudo -n dpkg -i /tmp/ika-ros2-apt-source.deb
fi
if ! grep -RqsE '^deb .* noble-updates |^Suites:.*noble-updates' /etc/apt/sources.list /etc/apt/sources.list.d; then
  printf '%s\n' 'deb https://ports.ubuntu.com/ubuntu-ports noble-updates main universe multiverse' 'deb https://ports.ubuntu.com/ubuntu-ports noble-backports main universe multiverse' 'deb https://ports.ubuntu.com/ubuntu-ports noble-security main universe multiverse' | sudo -n tee /etc/apt/sources.list.d/ika-ubuntu-updates.list >/dev/null
fi
echo '[2/4] Native ROS, motor/IMU/web and SLAM dependencies'
sudo -n apt-get update
sudo -n apt-get install -y --no-install-recommends ros-jazzy-ros-base ros-jazzy-robot-state-publisher ros-jazzy-xacro ros-jazzy-robot-localization ros-jazzy-rosbridge-server ros-jazzy-tf2-ros-py ros-jazzy-slam-toolbox python3-colcon-common-extensions python3-venv python3-yaml python3-pytest build-essential cmake git curl

# Gemstone minimal images can omit the CP2102 USB-to-serial module.
if ! modinfo cp210x >/dev/null 2>&1; then
  driver_package="kernel-module-cp210x-$(uname -r)"
  if apt-cache show "$driver_package" >/dev/null 2>&1; then
    sudo -n apt-get install -y --no-install-recommends "$driver_package"
    sudo -n depmod -a
  else
    echo "CP210x module unavailable for $(uname -r); install the matching USB serial driver before using the lidar." >&2
    exit 1
  fi
fi
sudo -n modprobe cp210x
echo '[3/4] GPIO v2 isolated environment'
python3 -m venv --system-site-packages "$HOME/ika-gpio-venv"
"$HOME/ika-gpio-venv/bin/pip" install 'gpiod>=2.2,<3'
echo '[4/4] Build project'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$HOME/ika-gpio-venv/lib/python3.12/site-packages:${PYTHONPATH:-}"
export CMAKE_BUILD_PARALLEL_LEVEL=2
export MAKEFLAGS=-j2
cd "$HOME/ika-ros"
if [ ! -d src/sllidar_ros2 ]; then
  git clone https://github.com/Slamtec/sllidar_ros2.git src/sllidar_ros2
fi
colcon build --symlink-install --executor sequential --cmake-args -DBUILD_TESTING=OFF
echo NATIVE_INSTALL_SUCCESS
