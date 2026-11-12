import pytest

from ika_line.line_math import LineFollower, read_line, read_line_analog, sensor_positions

POS5 = sensor_positions(5, 0.01)


def test_positions_left_positive_and_symmetric():
    assert POS5 == pytest.approx([0.02, 0.01, 0.0, -0.01, -0.02])


def test_read_line_centroid_and_flags():
    r = read_line([False, True, True, False, False], POS5)
    assert r.detected and r.position == pytest.approx(0.005)
    assert not read_line([False] * 5, POS5).detected
    assert read_line([True] * 5, POS5).intersection


def test_follower_turns_toward_line_and_slows():
    f = LineFollower(speed=0.2, half_width=0.02)
    v, w = f.update(read_line([True, False, False, False, False], POS5), 0.01)
    assert w > 0 and v < 0.2
    v, w = f.update(read_line([False, False, True, False, False], POS5), 0.01)
    assert v == pytest.approx(0.2)


def test_follower_searches_last_side_then_gives_up():
    f = LineFollower(lost_timeout=0.5)
    f.update(read_line([False, False, False, False, True], POS5), 0.01)   # sağda
    v, w = f.update(read_line([False] * 5, POS5), 0.1)
    assert f.state == 'searching' and v == 0.0 and w < 0
    for _ in range(10):
        v, w = f.update(read_line([False] * 5, POS5), 0.1)
    assert f.state == 'lost' and (v, w) == (0.0, 0.0)


def test_intersection_stop():
    f = LineFollower(intersection_action='stop')
    assert f.update(read_line([True] * 5, POS5), 0.01) == (0.0, 0.0)
    assert f.state == 'intersection'


def test_analog_position_between_sensors():
    pos = sensor_positions(2, 0.01)                      # 0.005, -0.005
    assert read_line_analog([1.0, 1.0], pos).position == pytest.approx(0.0)
    r = read_line_analog([1.0, 0.5], pos)                # çizgi sola yakın
    assert r.detected and 0.0 < r.position < 0.005
    assert r.sensors == [True, True]


def test_analog_ignores_white_noise_and_flags():
    r = read_line_analog([0.05, 0.0, 0.9, 0.0, 0.08], POS5)
    assert r.position == pytest.approx(0.0)              # gürültü kanalları ağırlık almaz
    assert not read_line_analog([0.4] * 5, POS5).detected
    assert read_line_analog([0.9] * 5, POS5).intersection


def test_filtered_derivative_smooths_step():
    raw = LineFollower(kp=0.0, kd=1.0)
    smooth = LineFollower(kp=0.0, kd=1.0, d_filter=0.8)
    for f in (raw, smooth):
        f.update(read_line_analog([0, 0, 1, 0, 0], POS5), 0.02)
    _, w_raw = raw.update(read_line_analog([0, 1, 0, 0, 0], POS5), 0.02)
    _, w_smooth = smooth.update(read_line_analog([0, 1, 0, 0, 0], POS5), 0.02)
    assert 0.0 < w_smooth < w_raw
