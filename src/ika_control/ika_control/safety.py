"""Lidar tabanlı çarpışma freni: robotun gideceği koridordaki en yakın engele
göre çizgisel hızı kısar (saf mantık, ROS'suz)."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Footprint:
    """Gövdenin base_link'e göre sınırları [m]."""

    front: float        # base_link -> ön uç (+x)
    rear: float         # base_link -> arka uç (-x yönünde, pozitif)
    half_width: float   # base_link -> yan kenar


@dataclass(frozen=True)
class LidarPose:
    """Lidarın base_link'e göre konumu."""

    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0


def corridor_gap(ranges, angle_min, angle_increment, lidar: LidarPose, body: Footprint,
                 forward: bool, side_margin: float = 0.0,
                 range_min=0.0, range_max=math.inf) -> float:
    """Hareket yönündeki koridorda (|y| <= yarım genişlik + side_margin) en yakın
    noktanın gövdenin ön (geri giderken arka) ucuna uzaklığı.

    Robotun yanındaki noktalar koridorda değildir; gövde ayak izinin içine düşen
    noktalar robotun kendi parçalarıdır ve yok sayılır.
    """
    lane = body.half_width + side_margin
    best = math.inf
    for i, r in enumerate(ranges):
        if math.isnan(r) or not (range_min < r < range_max):
            continue
        angle = lidar.yaw + angle_min + i * angle_increment
        x = lidar.x + r * math.cos(angle)
        y = lidar.y + r * math.sin(angle)
        if abs(y) > lane:
            continue
        gap = x - body.front if forward else -x - body.rear
        if 0.0 <= gap < best:
            best = gap
    return best


def limit_linear(linear: float, distance: float, stop_distance: float,
                 slow_distance: float) -> float:
    """distance <= stop -> 0; stop..slow arası doğrusal kısma; ötesi serbest."""
    if distance <= stop_distance:
        return 0.0
    if distance >= slow_distance or slow_distance <= stop_distance:
        return linear
    return linear * (distance - stop_distance) / (slow_distance - stop_distance)
