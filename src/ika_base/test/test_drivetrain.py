import pytest

from ika_base.config import DEFAULTS, flatten
from ika_base.drivetrain import GpioDrivetrain, SimDrivetrain
from ika_hal.gpio import MOCK_CHIP


def _cfg(**overrides):
    cfg = dict(DEFAULTS)
    cfg.update({
        'left.in1': 'GPIO22', 'left.in2': 'GPIO17', 'left.pwm': 'ecap0',
        'right.in1': 'GPIO24', 'right.in2': 'GPIO25', 'right.pwm': 'epwm1:1',
        'right.invert': True,
        'encoder.mode': 'none',
    })
    cfg.update(overrides)
    return cfg


def test_flatten_nested_yaml():
    assert flatten({'left': {'in1': 'x'}, 'a': 1}) == {'left.in1': 'x', 'a': 1}


def test_gpio_drivetrain_sets_direction_pins_and_pwm():
    dt = GpioDrivetrain(_cfg(), backend='mock')
    chip = dt._chips[MOCK_CHIP]
    dt.set_duty(40.0, 40.0)
    assert (chip.levels[22], chip.levels[17]) == (1, 0)
    assert (chip.levels[24], chip.levels[25]) == (0, 1)     # sağ motor ters bağlı
    assert dt.motors[0]._pwm.duty_percent == 40.0
    dt.set_duty(0.0, -30.0)
    assert (chip.levels[22], chip.levels[17]) == (0, 0)
    assert (chip.levels[24], chip.levels[25]) == (1, 0)
    dt.close()


def test_duplicate_pin_rejected():
    with pytest.raises(ValueError):
        GpioDrivetrain(_cfg(**{'right.in1': 'GPIO22'}), backend='mock')


def test_encoder_pin_clashing_with_motor_rejected():
    with pytest.raises(ValueError):
        GpioDrivetrain(_cfg(**{'encoder.mode': 'x4', 'left.enc_a': 'GPIO17',
                               'left.enc_b': 'GPIO5', 'right.enc_a': 'GPIO27',
                               'right.enc_b': 'GPIO23'}), backend='mock')


def test_missing_encoder_pins_rejected():
    with pytest.raises(ValueError):
        GpioDrivetrain(_cfg(**{'encoder.mode': 'x4'}), backend='mock')


def test_sim_drivetrain_moves_forward():
    dt = SimDrivetrain(_cfg(**{'backend': 'mock'}))
    dt.set_duty(50.0, 50.0)
    for _ in range(100):
        dt.step(0.02)
    left, right = dt.counts()
    assert left > right > 0      # sağ teker benzetimde biraz zayıf
