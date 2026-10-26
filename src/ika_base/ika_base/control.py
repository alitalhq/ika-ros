"""Teker hız kontrolü: ivme sınırlayıcı + ileri besleme destekli PI."""

import math


class SlewLimiter:
    """Hedef hızın değişimini max_accel [m/s^2] ile sınırlar."""

    def __init__(self, max_accel: float):
        self.max_accel = max_accel
        self.value = 0.0

    def step(self, target: float, dt: float) -> float:
        if self.max_accel <= 0.0:
            self.value = target
            return target
        max_step = self.max_accel * dt
        self.value += max(-max_step, min(max_step, target - self.value))
        return self.value

    def reset(self):
        self.value = 0.0


class WheelSpeedController:
    """Bir tekerin hızını [m/s] PWM duty yüzdesine [-100, 100] çevirir.

    duty = kff * hedef / max_speed * 100 + kp * hata + ki * ∫hata

    - kff: ileri besleme; 1.0 ve doğru max_speed ile PI sadece küçük
      düzeltme yapar, kazançlar düşük tutulabilir.
    - min_duty: motorun yerinden kalkması için gereken en düşük duty
      (statik sürtünme); hw_check ile ölçülür.
    - Doyumdayken integral büyütülmez (anti-windup).
    """

    def __init__(self, kp: float, ki: float, kff: float, max_speed: float,
                 min_duty: float = 0.0, max_duty: float = 100.0):
        if max_speed <= 0.0:
            raise ValueError('max_wheel_speed pozitif olmalı')
        self.kp = kp
        self.ki = ki
        self.kff = kff
        self.max_speed = max_speed
        self.min_duty = min_duty
        self.max_duty = max_duty
        self.integral = 0.0

    def reset(self):
        self.integral = 0.0

    def update(self, target: float, measured: float, dt: float) -> float:
        if abs(target) < 1e-4:
            self.reset()
            return 0.0
        if self.integral != 0.0 and math.copysign(1.0, self.integral) != math.copysign(1.0, target):
            # Yön değişti: eski yönde biriken integral yeni yönü frenlemesin.
            self.reset()

        error = target - measured
        feedforward = self.kff * target / self.max_speed * 100.0
        unclamped = feedforward + self.kp * error + self.ki * (self.integral + error * dt)
        saturated = abs(unclamped) >= self.max_duty
        if not saturated or math.copysign(1.0, error) != math.copysign(1.0, unclamped):
            self.integral += error * dt

        duty = feedforward + self.kp * error + self.ki * self.integral
        duty = max(-self.max_duty, min(self.max_duty, duty))
        if duty * target > 0.0 and abs(duty) < self.min_duty:
            duty = math.copysign(self.min_duty, duty)
        elif duty * target <= 0.0:
            # PI fren yönüne geçmek istiyorsa motoru boşa al; H-bridge'i
            # ters yöne sürmek tekeri titretir.
            duty = 0.0
        return duty


class LowPassFilter:

    def __init__(self, alpha: float):
        self.alpha = max(0.0, min(1.0, alpha))
        self.value = 0.0

    def step(self, sample: float) -> float:
        self.value += self.alpha * (sample - self.value)
        return self.value
