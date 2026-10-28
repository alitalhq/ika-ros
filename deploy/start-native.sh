#!/usr/bin/env bash
# Robotu Docker'sız başlatır (GPIO/PWM erişimi için root):
#   sudo bash deploy/start-native.sh [launch argümanları ...]
# Robot ayarları (ROS_DOMAIN_ID, IKA_ARGS) /etc/default/ika dosyasından okunur.
set -eo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OWNER_HOME="$(getent passwd "$(stat -c %U "$REPO")" | cut -d: -f6)"

[ -f /etc/default/ika ] && set -a && source /etc/default/ika && set +a
export ROS_LOG_DIR="${ROS_LOG_DIR:-/var/log/ika}"
mkdir -p "$ROS_LOG_DIR"

source /opt/ros/jazzy/setup.bash
source "$REPO/install/setup.bash"
export PYTHONPATH="$OWNER_HOME/ika-gpio-venv/lib/python3.12/site-packages:${PYTHONPATH:-}"

echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}  IKA_ARGS=${IKA_ARGS:-}"
# shellcheck disable=SC2086
exec ros2 launch ika_bringup robot.launch.py ${IKA_ARGS:-} "$@"
