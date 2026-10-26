"""Lidar tabanlı çarpışma freni: hareket yönündeki en yakın engele göre
çizgisel hızı kısar (saf mantık, ROS'suz)."""

import math


def _angle_diff(a: float, b: float) -> float:
    return math.atan2(math.sin(a - b), math.cos(a - b))


def sector_min(ranges, angle_min, angle_increment, center, half_width,
               range_min=0.0, range_max=math.inf) -> float:
    """center ± half_width [rad] (tarama çerçevesinde) içindeki en kısa geçerli mesafe."""
    best = math.inf
    for i, r in enumerate(ranges):
        if not (range_min < r < range_max) or math.isnan(r):
            continue
        if abs(_angle_diff(angle_min + i * angle_increment, center)) <= half_width and r < best:
            best = r
    return best


def limit_linear(linear: float, distance: float, stop_distance: float,
                 slow_distance: float) -> float:
    """distance <= stop -> 0; stop..slow arası doğrusal kısma; ötesi serbest."""
    if distance <= stop_distance:
        return 0.0
    if distance >= slow_distance or slow_distance <= stop_distance:
        return linear
    return linear * (distance - stop_distance) / (slow_distance - stop_distance)
