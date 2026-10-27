import math

import pytest

from ika_base.kinematics import (
    WheelOdometry, counts_to_distance, limit_wheels, twist_to_wheels, wheels_to_twist)


def test_twist_round_trip():
    left, right = twist_to_wheels(0.2, 1.0, 0.2)
    assert left == pytest.approx(0.1) and right == pytest.approx(0.3)
    assert wheels_to_twist(left, right, 0.2) == pytest.approx((0.2, 1.0))


def test_limit_preserves_curvature():
    left, right = limit_wheels(0.2, 1.0, 0.5)
    assert right == pytest.approx(0.5)
    assert left / right == pytest.approx(0.2)
    assert limit_wheels(0.1, -0.2, 0.5) == (0.1, -0.2)


def test_counts_to_distance_one_revolution():
    assert counts_to_distance(1400, 1400, 0.05) == pytest.approx(2 * math.pi * 0.05)


def test_odometry_straight_then_turn_in_place():
    odom = WheelOdometry(0.2)
    odom.update(1.0, 1.0)
    assert (odom.pose.x, odom.pose.y) == pytest.approx((1.0, 0.0))
    quarter = math.pi / 2 * 0.1          # yerinde 90° için teker yolu
    odom.update(-quarter, quarter)
    assert odom.pose.theta == pytest.approx(math.pi / 2)
    assert odom.pose.x == pytest.approx(1.0)
    odom.update(0.5, 0.5)
    assert (odom.pose.x, odom.pose.y) == pytest.approx((1.0, 0.5))
