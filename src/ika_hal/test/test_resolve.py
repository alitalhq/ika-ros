import os

import pytest

from ika_hal.gpio import MOCK_CHIP, resolve_pin
from ika_hal.pwm import describe_pwm_chips, resolve_pwm


def test_resolve_pin_numeric_and_empty():
    assert resolve_pin('gpiochip2:41') == ('gpiochip2', 41)
    assert resolve_pin('/dev/gpiochip3:7') == ('gpiochip3', 7)
    assert resolve_pin('  ') is None


def test_resolve_pin_names_in_mock():
    assert resolve_pin('GPIO22', 'mock') == (MOCK_CHIP, 22)
    assert resolve_pin('gpio-5', 'mock') == (MOCK_CHIP, 5)
    with pytest.raises(ValueError):
        resolve_pin('pin15', 'mock')


def _fake_sysfs(tmp_path, chips):
    """chips: {pwmchip numarası: aygıt adı} -> sahte /sys/class/pwm."""
    base = tmp_path / 'class_pwm'
    base.mkdir()
    for number, device in chips.items():
        target = tmp_path / 'devices' / device / 'pwm' / f'pwmchip{number}'
        target.mkdir(parents=True)
        os.symlink(target, base / f'pwmchip{number}')
    return str(base)


def test_resolve_pwm_by_module_address(tmp_path):
    # Yalnızca bazı overlay'ler yüklü: numaralar belgedeki tablodan kaymış.
    base = _fake_sysfs(tmp_path, {0: '23100000.pwm', 1: '23120000.pwm', 2: '23010000.pwm'})
    assert resolve_pwm('ecap0', base=base) == (0, 0)
    assert resolve_pwm('ecap2', base=base) == (1, 0)
    assert resolve_pwm('epwm1:1', base=base) == (2, 1)
    assert resolve_pwm('3:0', base=base) == (3, 0)
    assert resolve_pwm('', base=base) is None
    with pytest.raises(ValueError, match='ecap1'):
        resolve_pwm('ecap1', base=base)
    assert describe_pwm_chips(base)[1] == 'pwmchip1 -> 23120000.pwm (ecap2)'


def test_resolve_pwm_rejects_bad_spec():
    with pytest.raises(ValueError):
        resolve_pwm('ecap9', 'mock')
    with pytest.raises(ValueError):
        resolve_pwm('epwm1:x', 'mock')
