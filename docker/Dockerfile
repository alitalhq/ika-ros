# İKA robot imajı — Ubuntu 24.04 + ROS 2 Jazzy (arm64 Gemstone ve amd64 PC).
#   docker compose build      # repo kökünden
FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]
WORKDIR /ika_ws

# Önce yalnızca bağımlılık bildirimleri: kaynak değişince bu katman yeniden kurulmaz.
COPY ika.repos .
RUN mkdir -p src && vcs import src < ika.repos
COPY src/ika_interfaces/package.xml src/ika/ika_interfaces/
COPY src/ika_description/package.xml src/ika/ika_description/
COPY src/ika_hal/package.xml src/ika/ika_hal/
COPY src/ika_base/package.xml src/ika/ika_base/
COPY src/ika_imu/package.xml src/ika/ika_imu/
COPY src/ika_line/package.xml src/ika/ika_line/
COPY src/ika_control/package.xml src/ika/ika_control/
COPY src/ika_navigation/package.xml src/ika/ika_navigation/
COPY src/ika_gcs/package.xml src/ika/ika_gcs/
COPY src/ika_bringup/package.xml src/ika/ika_bringup/
RUN apt-get update \
    && rosdep update --rosdistro jazzy \
    && rosdep install --from-paths src --ignore-src -y \
    && apt-get install -y --no-install-recommends python3-pip \
    && rm -rf /var/lib/apt/lists/*

# libgpiod v2 Python bağlaması (Ubuntu 24.04 apt'ında yalnızca v1.6 var).
# v2: enkoder olayları için 1024'lük kernel tamponu ve tek sıralı kuyruk;
# v1 hat başına 16 olayla yüksek devirde sayım kaçırır. apt'taki v1'in önüne geçer.
RUN pip install --no-cache-dir --break-system-packages "gpiod>=2.2,<3"

COPY src src/ika
RUN source /opt/ros/jazzy/setup.bash \
    && colcon build --symlink-install --event-handlers console_cohesion-

COPY docker/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "ika_bringup", "robot.launch.py"]
