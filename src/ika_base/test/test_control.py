import pytest

from ika_base.control import SlewLimiter, WheelSpeedController


def test_slew_limiter_ramps():
    ramp = SlewLimiter(1.0)
    assert ramp.step(1.0, 0.1) == pytest.approx(0.1)
    for _ in range(20):
        ramp.step(1.0, 0.1)
    assert ramp.value == pytest.approx(1.0)


def test_zero_target_gives_zero_and_resets():
    pid = WheelSpeedController(50, 200, 1.0, 0.5)
    pid.update(0.3, 0.0, 0.02)
    assert pid.integral != 0.0
    assert pid.update(0.0, 0.2, 0.02) == 0.0
    assert pid.integral == 0.0


def test_feedforward_only_at_steady_state():
    pid = WheelSpeedController(50, 200, 1.0, 0.5)
    assert pid.update(0.25, 0.25, 0.02) == pytest.approx(50.0)


def test_anti_windup_when_saturated():
    pid = WheelSpeedController(50, 200, 1.0, 0.5)
    for _ in range(500):
        duty = pid.update(0.5, 0.0, 0.02)   # motor sıkışmış
    assert duty == pytest.approx(100.0)
    assert pid.ki * pid.integral < 50.0


def test_min_duty_and_no_reverse_braking():
    pid = WheelSpeedController(50, 0, 1.0, 0.5, min_duty=15.0)
    assert pid.update(0.01, 0.0, 0.02) == pytest.approx(15.0)
    # Çok hızlı dönüyor: düzeltme ters yöne itmek yerine boşa almalı.
    assert pid.update(0.05, 0.5, 0.02) == 0.0


def test_closed_loop_converges_on_simple_motor():
    pid = WheelSpeedController(60, 300, 1.0, 0.5)
    speed = 0.0
    for _ in range(300):
        duty = pid.update(0.3, speed, 0.02)
        # Gerçek motor %10 daha zayıf ve 8% ölü bölgeli
        effective = 0.0 if abs(duty) < 8 else duty
        speed += (effective / 100 * 0.45 - speed) * 0.2
    assert speed == pytest.approx(0.3, abs=0.01)


def test_integral_authority_is_limited_when_measurement_drops():
    # Hız ölçümü 2 s sıfır kalır (pil çöktü / enkoder sustu): duty hedefin
    # gerektirdiği ileri beslemenin en fazla kp*hata + i_limit üstüne çıkar.
    pid = WheelSpeedController(60, 300, 1.0, 0.8, i_limit=30.0)
    for _ in range(100):
        duty = pid.update(0.3, 0.0, 0.02)
    assert pid.ki * pid.integral == pytest.approx(30.0)
    assert duty == pytest.approx(37.5 + 60 * 0.3 + 30.0)   # %85.5, %100 değil


def test_turn_survives_measurement_dropout():
    # W + A: sol 0.30, sağ 0.50 hedef; ölçüm düşükken bile duty'ler farklı kalır.
    left = WheelSpeedController(60, 300, 1.0, 0.8, i_limit=30.0)
    right = WheelSpeedController(60, 300, 1.0, 0.8, i_limit=30.0)
    for _ in range(100):
        dl = left.update(0.30, 0.0, 0.02)
        dr = right.update(0.50, 0.0, 0.02)
    assert dr - dl > 10.0
