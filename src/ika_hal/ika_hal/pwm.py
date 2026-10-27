"""Linux sysfs PWM (/sys/class/pwm/pwmchipN/pwmM) ve donanımsız mock PWM.

Gemstone O1 PWM kanalları (docs.t3gemstone.org, PWM sayfası); her biri
/boot/uEnv.txt `overlays=` satırına overlay eklenerek açılır:

    ecap0    GPIO12   pwm-ecap0-gpio12
    ecap1    GPIO16   pwm-ecap1-gpio16
    ecap2    GPIO18   pwm-ecap2-gpio18
    epwm0:0  GPIO5    pwm-epwm0-gpio5      (epwm0:1 = GPIO14, UART TX'i kapatır)
    epwm1:0  GPIO6    pwm-epwm1-gpio6
    epwm1:1  GPIO13   pwm-epwm1-gpio13

pwmchipN numaraları yüklü overlay'lere göre DEĞİŞEBİLİR; bu yüzden kanal
modül adıyla verilir ve aygıt yolundaki bellek adresinden bulunur. Bir epwm
modülünün iki kanalı aynı periyodu paylaşmak zorundadır.

Yazım: "ecap0", "epwm1:1" veya numara ile "3:0" (pwmchip3/pwm0). "" = yok.
"""

import glob
import os
import time

_BASE = '/sys/class/pwm'

# AM62x / AM67A (J722S) ailesi bellek adresleri. Kartta doğrulamak için:
#   ls -l /sys/class/pwm/
PWM_MODULES = {
    'epwm0': '23000000', 'epwm1': '23010000', 'epwm2': '23020000',
    'ecap0': '23100000', 'ecap1': '23110000', 'ecap2': '23120000',
}


def describe_pwm_chips(base: str = _BASE) -> list:
    """['pwmchip0 -> 23100000.pwm (ecap0)', ...]"""
    rows = []
    for path in sorted(glob.glob(f'{base}/pwmchip*'), key=lambda p: int(p.rsplit('chip', 1)[1])):
        device = os.path.basename(os.path.dirname(os.path.dirname(os.path.realpath(path))))
        module = next((m for m, addr in PWM_MODULES.items() if device.startswith(addr + '.')), '?')
        rows.append(f'{os.path.basename(path)} -> {device} ({module})')
    return rows


def resolve_pwm(spec: str, backend: str = 'gpiod', base: str = _BASE):
    """PWM yazımını (chip_no, kanal) çiftine çevirir; boş -> None."""
    spec = (spec or '').strip().lower()
    if not spec:
        return None
    name, _, channel = spec.partition(':')
    if channel and not channel.isdigit():
        raise ValueError(f"PWM '{spec}' geçersiz; ör. 'ecap0', 'epwm1:1', '3:0'")
    channel = int(channel or 0)
    if name.isdigit():
        return int(name), channel
    if name not in PWM_MODULES:
        raise ValueError(f"bilinmeyen PWM modülü '{name}'; geçerli: {', '.join(PWM_MODULES)}")
    if backend == 'mock':
        return list(PWM_MODULES).index(name), channel
    for path in glob.glob(f'{base}/pwmchip*'):
        if f'/{PWM_MODULES[name]}.' in os.path.realpath(path):
            return int(path.rsplit('chip', 1)[1]), channel
    found = '; '.join(describe_pwm_chips(base)) or 'hiç pwmchip yok'
    raise ValueError(f"'{name}' PWM çipi bulunamadı (overlay açık mı?). Mevcut: {found}")


class SysfsPwm:

    def __init__(self, chip: int, channel: int, period_ns: int = 1_000_000, base: str = _BASE):
        if chip < 0 or channel < 0:
            raise ValueError('pwm chip ve channel >= 0 olmalı')
        self._chip_path = f'{base}/pwmchip{chip}'
        self._pwm_path = f'{self._chip_path}/pwm{channel}'
        self.duty_percent = 0.0
        self.note = ''

        if not os.path.isdir(self._pwm_path):
            self._write(f'{self._chip_path}/export', channel)
            # export yeni bir udev olayı tetikler; izin kuralı asenkron
            # uygulandığı için ilk yazmadan önce dosyanın açılmasını bekle.
            self._wait_writable(f'{self._pwm_path}/period')

        # Period değişmeden önce enable kapatılmazsa sysfs "duty > period"
        # hatası verebiliyor.
        try:
            self._write(f'{self._pwm_path}/enable', 0)
        except OSError:
            pass
        self._write(f'{self._pwm_path}/duty_cycle', 0)
        self.period_ns = self._set_period(int(period_ns), channel)
        self._write(f'{self._pwm_path}/enable', 1)

    def _set_period(self, period_ns: int, channel: int) -> int:
        try:
            self._write(f'{self._pwm_path}/period', period_ns)
            return period_ns
        except OSError:
            # epwm'in iki kanalı periyot paylaşır: kardeş kanal zaten başka
            # periyotla çalışıyorsa onunkine uy.
            sibling = f'{self._chip_path}/pwm{1 - channel}/period' if channel in (0, 1) else ''
            if not sibling or not os.path.exists(sibling):
                raise
            with open(sibling) as f:
                shared = int(f.read().strip())
            self._write(f'{self._pwm_path}/period', shared)
            self.note = (f'periyot {period_ns} ns yazılamadı, kardeş kanalın '
                         f'periyodu {shared} ns kullanılıyor')
            return shared

    @staticmethod
    def _wait_writable(path: str, timeout_s: float = 1.0):
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if os.access(path, os.W_OK):
                return
            time.sleep(0.02)

    @staticmethod
    def _write(path: str, value):
        with open(path, 'w') as f:
            f.write(str(value))

    def set_duty_percent(self, percent: float):
        percent = max(0.0, min(100.0, float(percent)))
        if percent == self.duty_percent:
            return
        self._write(f'{self._pwm_path}/duty_cycle', int(self.period_ns * percent / 100.0))
        self.duty_percent = percent

    def release(self):
        try:
            self._write(f'{self._pwm_path}/duty_cycle', 0)
            self._write(f'{self._pwm_path}/enable', 0)
        except OSError:
            pass


class MockPwm:

    def __init__(self, chip: int = 0, channel: int = 0, period_ns: int = 1_000_000):
        self.duty_percent = 0.0
        self.period_ns = period_ns
        self.note = ''

    def set_duty_percent(self, percent: float):
        self.duty_percent = max(0.0, min(100.0, float(percent)))

    def release(self):
        self.duty_percent = 0.0


def open_pwm(spec: str, period_ns: int, backend: str = 'gpiod'):
    """spec: 'ecap0' / 'epwm1:1' / '3:0'; boş -> None."""
    resolved = resolve_pwm(spec, backend)
    if resolved is None:
        return None
    if backend == 'mock':
        return MockPwm(*resolved, period_ns)
    return SysfsPwm(*resolved, period_ns)
