#!/usr/bin/env bash
# Robotu açılışta başlatan systemd servisini kurar:
#   sudo bash deploy/install-service.sh <robot-no>
# robot-no ROS_DOMAIN_ID olur (1, 2, ...). Aynı ağdaki her robota farklı
# numara verin; yoksa bir robotun arayüzünden verilen komut diğerini de sürer.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ID="${1:?kullanım: sudo bash deploy/install-service.sh <robot-no (1-101)>}"
if ! [[ "$ID" =~ ^[0-9]+$ ]] || [ "$ID" -gt 101 ]; then
  echo "robot-no 0-101 arası bir sayı olmalı" >&2
  exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
  echo "sudo ile çalıştırın" >&2
  exit 1
fi

if [ -f /etc/default/ika ]; then
  sed -i "s/^ROS_DOMAIN_ID=.*/ROS_DOMAIN_ID=$ID/" /etc/default/ika
else
  cat > /etc/default/ika <<CONF
# İKA robot ayarları (deploy/start-native.sh okur).
# Aynı ağdaki her robotun ROS_DOMAIN_ID'si farklı olmalı.
ROS_DOMAIN_ID=$ID
# Ek launch argümanları, ör.: IKA_ARGS="line:=false" veya
# IKA_ARGS="slam_mode:=localization map:=~/ika_maps/salon nav:=true"
IKA_ARGS=""
CONF
fi

cat > /etc/systemd/system/ika.service <<UNIT
[Unit]
Description=IKA ROS 2 robot ve web arayüzü
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
ExecStart=/bin/bash $REPO/deploy/start-native.sh
Restart=on-failure
RestartSec=5
KillSignal=SIGINT
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
UNIT

# PR #3'teki ilk servis adı
if systemctl list-unit-files ika-native.service >/dev/null 2>&1; then
  systemctl disable --now ika-native.service 2>/dev/null || true
  rm -f /etc/systemd/system/ika-native.service
fi
systemctl daemon-reload
systemctl enable --now ika.service
echo "Servis kuruldu: ROS_DOMAIN_ID=$ID. Durum: systemctl status ika  Log: journalctl -u ika -f"
