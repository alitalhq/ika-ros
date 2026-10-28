import math

import pytest

from ika_control.safety import corridor_gap, Footprint, LidarPose, limit_linear

BODY = Footprint(front=0.17, rear=0.09, half_width=0.09)


def _scan(points, n=720):
    """(x, y) noktalarını lidar merkezli (lidar = base_link) bir taramaya yazar."""
    inc = 2 * math.pi / n
    ranges = [math.inf] * n
    for x, y in points:
        i = round((math.atan2(y, x) + math.pi) / inc) % n
        ranges[i] = min(ranges[i], math.hypot(x, y))
    return ranges, -math.pi, inc


def gap(points, forward=True, lidar=LidarPose(), margin=0.0):
    return corridor_gap(*_scan(points), lidar, BODY, forward, side_margin=margin)


def test_obstacle_ahead_measured_from_front_edge():
    assert gap([(0.47, 0.0)]) == pytest.approx(0.30, abs=0.005)


def test_side_wall_does_not_block():
    # Robotun 2 cm yanında, boydan boya duvar: koridorda değil.
    wall = [(x / 100, 0.11) for x in range(-30, 60)]
    assert gap(wall) == math.inf


def test_wall_ahead_inside_lane_blocks():
    wall = [(0.30, y / 100) for y in range(-50, 51)]
    assert gap(wall) == pytest.approx(0.13, abs=0.005)


def test_side_margin_widens_lane():
    assert gap([(0.40, 0.11)]) == math.inf
    assert gap([(0.40, 0.11)], margin=0.03) == pytest.approx(0.23, abs=0.005)


def test_points_on_the_robot_are_ignored():
    # Lidar direği / kablo: gövdenin içinde.
    assert gap([(0.05, 0.02), (-0.05, -0.03), (0.10, 0.08)]) == math.inf


def test_reverse_uses_rear_edge():
    assert gap([(-0.39, 0.0)], forward=False) == pytest.approx(0.30, abs=0.005)
    assert gap([(0.30, 0.0)], forward=False) == math.inf


def test_lidar_mounted_backwards():
    # Lidar 180° ters takılı: ileri yöndeki engel taramada arkada görünür.
    ranges, amin, inc = _scan([(-0.47, 0.0)])
    turned = LidarPose(yaw=math.pi)
    assert corridor_gap(ranges, amin, inc, turned, BODY, True) == pytest.approx(0.30, abs=0.005)
    assert corridor_gap(ranges, amin, inc, LidarPose(), BODY, True) == math.inf


def test_lidar_offset_from_base_link():
    ranges, amin, inc = _scan([(0.30, 0.0)])
    ahead = LidarPose(x=0.05)
    assert corridor_gap(ranges, amin, inc, ahead, BODY, True) == pytest.approx(0.18, abs=0.005)


def test_invalid_ranges_ignored():
    ranges, amin, inc = _scan([])
    mid = len(ranges) // 2
    ranges[mid] = 0.0
    ranges[mid + 1] = float('nan')
    assert corridor_gap(ranges, amin, inc, LidarPose(), BODY, True,
                        range_min=0.05, range_max=12.0) == math.inf


def test_limit_linear():
    assert limit_linear(0.4, 0.1, 0.2, 0.5) == 0.0
    assert limit_linear(0.4, 0.35, 0.2, 0.5) == pytest.approx(0.2)
    assert limit_linear(0.4, 1.0, 0.2, 0.5) == 0.4
