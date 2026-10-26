"""Motor + enkoder donanımını tek arayüzde toplar.

    dt = build_drivetrain(cfg)      # cfg: config.DEFAULTS biçiminde sözlük
    dt.set_duty(sol, sag)           # -100..100
    dt.step(dt_s)                   # sadece benzetimde iş yapar
    dt.counts()                     # (sol, sag) kümülatif enkoder sayımı veya None
    dt.close()

GpioDrivetrain gerçek donanımı, SimDrivetrain (backend: mock) basit bir
motor modeliyle enkoder üretir; üst katman ikisini ayırt etmez.
"""

import math

from ika_base.encoder import EncoderReader, multiplier
from ika_hal.gpio import open_chip, resolve_pin
from ika_hal.pwm import open_pwm


class HBridgeMotor:
    """in_in_pwm: IN1/IN2 yön, EN hattına PWM (L298N, TB6612, ...)
    dir_pwm:   tek DIR hattı + PWM (in2 kullanılmaz)
    PWM yoksa (EN jumper'lı) motor yalnızca tam hız / dur çalışır."""

    def __init__(self, in1, in2, pwm, mode='in_in_pwm', invert=False, brake=False):
        if mode not in ('in_in_pwm', 'dir_pwm'):
            raise ValueError(f"motor_driver in_in_pwm veya dir_pwm olmalı, gelen: {mode!r}")
        if in1 is None or (mode == 'in_in_pwm' and in2 is None):
            raise ValueError(f'{mode} için yön pinleri tanımlanmalı')
        self._in1 = in1      # (request, offset)
        self._in2 = in2
        self._pwm = pwm
        self._mode = mode
        self._invert = invert
        self._brake = brake

    @staticmethod
    def _set(pin, value):
        if pin is not None:
            pin[0].set(pin[1], value)

    def drive(self, duty: float):
        if self._invert:
            duty = -duty
        if self._pwm is None:
            duty = math.copysign(100.0, duty) if abs(duty) >= 20.0 else 0.0
        forward, backward = duty > 0.0, duty < 0.0
        if self._mode == 'dir_pwm':
            self._set(self._in1, 1 if forward else 0)
        elif forward or backward:
            self._set(self._in1, 1 if forward else 0)
            self._set(self._in2, 1 if backward else 0)
        else:
            self._set(self._in1, 1 if self._brake else 0)
            self._set(self._in2, 1 if self._brake else 0)
        if self._pwm is not None:
            self._pwm.set_duty_percent(abs(duty))

    def close(self):
        self.drive(0.0)
        if self._pwm is not None:
            self._pwm.release()


class GpioDrivetrain:

    def __init__(self, cfg: dict, backend: str = 'gpiod'):
        self._chips = {}
        self._requests = []
        self.encoders = None
        self.motors = []

        pins = {key: resolve_pin(cfg[key], backend) for key in (
            'left.in1', 'left.in2', 'right.in1', 'right.in2',
            'left.enc_a', 'left.enc_b', 'right.enc_a', 'right.enc_b')}
        used = [p for p in pins.values() if p]
        if len(set(used)) != len(used):
            raise ValueError(f'aynı GPIO hattı iki kez kullanılmış: {pins}')

        # Tüm çıkışları chip başına tek istekte topla.
        outputs = {}
        for side in ('left', 'right'):
            for key in ('in1', 'in2'):
                pin = pins[f'{side}.{key}']
                if pin:
                    outputs.setdefault(pin[0], []).append(pin[1])
        out_req = {}
        for chip_name, offsets in outputs.items():
            req = self._chip(chip_name, backend).request_outputs(offsets, consumer='ika_base')
            self._requests.append(req)
            out_req[chip_name] = req

        def out_pin(key):
            pin = pins[key]
            return (out_req[pin[0]], pin[1]) if pin else None

        self.notes = []
        for side in ('left', 'right'):
            pwm = open_pwm(cfg[f'{side}.pwm'], cfg['pwm_period_ns'], backend)
            if pwm is not None and pwm.note:
                self.notes.append(f'{side}: {pwm.note}')
            self.motors.append(HBridgeMotor(
                out_pin(f'{side}.in1'), out_pin(f'{side}.in2'), pwm,
                mode=cfg['motor_driver'], invert=cfg[f'{side}.invert'],
                brake=cfg['brake_on_stop']))

        if cfg['encoder.mode'] != 'none':
            encoders = []
            for side in ('left', 'right'):
                a, b = pins[f'{side}.enc_a'], pins[f'{side}.enc_b']
                if a is None or b is None:
                    raise ValueError(f'{side} enkoder pinleri (enc_a / enc_b) tanımlanmalı '
                                     "veya encoder.mode: none verilmeli")
                encoders.append((a, b, cfg[f'{side}.enc_invert']))
            self.encoders = EncoderReader(
                lambda name: self._chip(name, backend), encoders,
                mode=cfg['encoder.mode'], bias=cfg['encoder.bias'])

    def _chip(self, name, backend):
        if name not in self._chips:
            self._chips[name] = open_chip(name, backend)
        return self._chips[name]

    def set_duty(self, left: float, right: float):
        self.motors[0].drive(left)
        self.motors[1].drive(right)

    def step(self, dt: float):
        pass

    def counts(self):
        return tuple(self.encoders.counts()) if self.encoders else None

    def encoder_errors(self):
        return tuple(self.encoders.errors()) if self.encoders else (0, 0)

    def close(self):
        for motor in self.motors:
            motor.close()
        if self.encoders:
            self.encoders.close()
        for req in self._requests:
            req.release()


class SimDrivetrain:
    """Donanımsız benzetim: teker hızı duty'ye birinci dereceden yanıt verir
    (tau), altına küçük bir ölü bölge ve sol/sağ verim farkı eklenir; PID
    gerçekten bir şeyi düzeltiyor olsun diye."""

    def __init__(self, cfg: dict, tau: float = 0.12, dead_duty: float = 8.0,
                 right_gain: float = 0.93):
        self._max_speed = cfg['max_wheel_speed']
        self._cpr = cfg['encoder.ppr'] * multiplier(cfg['encoder.mode']) or 1000.0
        self._radius = cfg['wheel_radius']
        self._tau = tau
        self._dead = dead_duty
        self._gains = (1.0, right_gain)
        self._duty = [0.0, 0.0]
        self._speed = [0.0, 0.0]
        self._pos = [0.0, 0.0]
        self.counts_per_rev = self._cpr

    def set_duty(self, left: float, right: float):
        self._duty = [left, right]

    def step(self, dt: float):
        for i in range(2):
            duty = self._duty[i]
            effective = 0.0 if abs(duty) < self._dead else duty
            target = effective / 100.0 * self._max_speed * self._gains[i]
            self._speed[i] += (target - self._speed[i]) * min(1.0, dt / self._tau)
            self._pos[i] += self._speed[i] * dt

    def counts(self):
        per_m = self._cpr / (2.0 * math.pi * self._radius)
        return int(self._pos[0] * per_m), int(self._pos[1] * per_m)

    def encoder_errors(self):
        return (0, 0)

    def close(self):
        pass


def build_drivetrain(cfg: dict):
    if cfg['backend'] == 'mock':
        return SimDrivetrain(cfg)
    return GpioDrivetrain(cfg, cfg['backend'])
