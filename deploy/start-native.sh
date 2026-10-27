#!/usr/bin/env bash
set -e
export ROS_LOG_DIR=/var/log/ika-native
mkdir -p "$ROS_LOG_DIR"
source /opt/ros/jazzy/setup.bash
source /home/gemstone/ika-ros/install/setup.bash
export PYTHONPATH="/home/gemstone/ika-gpio-venv/lib/python3.12/site-packages:${PYTHONPATH:-}"
exec ros2 launch ika_bringup robot.launch.py \
  hardware:=/home/gemstone/ika-ros/deploy/hardware-usb-lidar.yaml \
  lidar:=true lidar_motor:=false \
  lidar_port:=/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0 \
  line:=true slam:=true "$@"
