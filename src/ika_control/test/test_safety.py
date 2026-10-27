import math

import pytest

from ika_control.safety import limit_linear, sector_min


def _scan(n=360):
    return [5.0] * n, -math.pi, 2 * math.pi / n


def test_sector_min_front_and_rear():
    ranges, amin, inc = _scan()
    ranges[180] = 0.3      # tam önde (0 rad)
    ranges[0] = 0.1        # arkada (-pi)
    assert sector_min(ranges, amin, inc, 0.0, math.radians(20)) == pytest.approx(0.3)
    assert sector_min(ranges, amin, inc, math.pi, math.radians(20)) == pytest.approx(0.1)


def test_sector_min_ignores_invalid():
    ranges, amin, inc = _scan()
    ranges[180] = 0.0
    ranges[181] = float('inf')
    ranges[182] = float('nan')
    assert sector_min(ranges, amin, inc, 0.0, 0.2, range_min=0.05, range_max=12.0) == 5.0


def test_limit_linear():
    assert limit_linear(0.4, 0.1, 0.2, 0.5) == 0.0
    assert limit_linear(0.4, 0.35, 0.2, 0.5) == pytest.approx(0.2)
    assert limit_linear(0.4, 1.0, 0.2, 0.5) == 0.4
