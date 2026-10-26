from ika_hal.gpio import open_chip
from ika_hal.pwm import open_pwm


def test_mock_outputs_and_inputs():
    chip = open_chip('gpiochip0', backend='mock')
    out = chip.request_outputs([1, 2])
    out.set(1, 1)
    assert chip.levels[1] == 1 and chip.levels[2] == 0

    inp = chip.request_inputs([5, 6], bias='pull-up')
    chip.set_level(6, 1)
    assert inp.get_all() == [0, 1]


def test_mock_edges_only_reach_requested_lines():
    chip = open_chip('gpiochip0', backend='mock')
    ev = chip.request_edges([3, 4])
    chip.inject_edge(3, 1)
    chip.inject_edge(9, 1)
    assert ev.wait(0.0)
    edges = ev.read()
    assert [(e.offset, e.level) for e in edges] == [(3, 1)]
    assert not ev.wait(0.0)


def test_mock_pwm_clamps():
    pwm = open_pwm('ecap0', 1_000_000, backend='mock')
    pwm.set_duty_percent(150)
    assert pwm.duty_percent == 100.0
