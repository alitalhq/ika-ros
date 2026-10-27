from ika_control.mux import CommandMux


def test_only_active_mode_source_passes():
    mux = CommandMux(timeout=0.5)
    mux.feed('line', 0.2, 0.1, 0.0)
    assert mux.output(0.0) == (0.0, 0.0)          # idle
    assert mux.set_mode('line')[0]
    mux.feed('line', 0.2, 0.1, 1.0)
    mux.feed('nav', 0.5, 0.0, 1.0)
    assert mux.output(1.1) == (0.2, 0.1)
    assert mux.output(2.0) == (0.0, 0.0)          # zaman aşımı


def test_teleop_takeover_and_disable():
    mux = CommandMux()
    mux.set_mode('line')
    assert mux.feed('teleop', 0.0, 0.0, 0.0) is None    # sıfır komut devralmaz
    assert mux.feed('teleop', 0.1, 0.0, 0.0) == 'manual'
    assert mux.output(0.1) == (0.1, 0.0)
    strict = CommandMux(teleop_takeover=False)
    strict.set_mode('line')
    assert strict.feed('teleop', 0.1, 0.0, 0.0) is None and strict.mode == 'line'


def test_estop_blocks_everything():
    mux = CommandMux()
    mux.set_mode('manual')
    mux.feed('teleop', 0.3, 0.0, 0.0)
    mux.set_estop(True)
    assert mux.mode == 'idle' and mux.output(0.0) == (0.0, 0.0)
    assert not mux.set_mode('manual')[0]
    assert mux.feed('teleop', 0.3, 0.0, 0.1) is None
    mux.set_estop(False)
    assert mux.set_mode('manual')[0]


def test_unknown_mode_and_stale_command_on_switch():
    mux = CommandMux()
    assert not mux.set_mode('dance')[0]
    mux.feed('nav', 0.3, 0.0, 0.0)
    mux.set_mode('nav')
    assert mux.output(0.1) == (0.0, 0.0)          # moda girmeden önceki komut sızmaz
