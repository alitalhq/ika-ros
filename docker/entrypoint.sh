#!/bin/bash
set -e
source /opt/ros/jazzy/setup.bash
source /ika_ws/install/setup.bash
exec "$@"
