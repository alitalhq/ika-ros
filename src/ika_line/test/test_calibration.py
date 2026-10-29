import json

import pytest

from ika_line.calibration import CalibrationSession


def samples(session, value, start):
    for i in range(51):
        now = start + i * 0.02
        session.set_command([0.0] * 6, now)
        session.feed([value] * 8, now)
    return now


def session(tmp_path):
    result = CalibrationSession(str(tmp_path / 'calibration.json'))
    result.set_mode('idle')
    return result


def test_persists_only_after_two_distinct_surfaces(tmp_path):
    s = session(tmp_path)
    old = {'white_mv': [500] * 8, 'black_mv': [2500] * 8}
    path = tmp_path / 'calibration.json'
    path.write_text(json.dumps(old))
    now = samples(s, 1000, 10)
    assert s.capture('white', now) is None
    assert json.loads(path.read_text()) == old
    with pytest.raises(ValueError):
        s.capture('black', now)
    now = samples(s, 2800, now + 0.02)
    calibration = s.capture('black', now)
    assert json.loads(path.read_text()) == calibration
    assert s.status(calibration, now)['threshold_mv'] == [1900] * 8
    assert not s.status(calibration, now)['white_ready']


def test_failed_separation_preserves_previous_file_and_allows_retry(tmp_path):
    s = session(tmp_path)
    path = tmp_path / 'calibration.json'
    path.write_text('previous calibration')
    now = samples(s, 1000, 10)
    s.capture('white', now)
    now = samples(s, 1050, now + 0.02)
    with pytest.raises(ValueError, match='D1'):
        s.capture('black', now)
    assert path.read_text() == 'previous calibration'
    now = samples(s, 2900, now + 0.02)
    assert s.capture('black', now)['black_mv'] == [2900] * 8


@pytest.mark.parametrize('reason', ['mode', 'motion', 'stale_command', 'stale_sensor'])
def test_rejects_nonstationary_or_stale_measurement(tmp_path, reason):
    s = session(tmp_path)
    now = samples(s, 1000, 10)
    if reason == 'mode':
        s.set_mode('line')
    elif reason == 'motion':
        s.set_command([0, 0, 0, 0, 0, 0.1], now)
    elif reason == 'stale_command':
        now += 0.6
    else:
        now += 0.6
        s.set_command([0] * 6, now)
    with pytest.raises(ValueError):
        s.capture('white', now)
    assert not (tmp_path / 'calibration.json').exists()


def test_reconnect_and_mode_change_invalidate_pending_white(tmp_path):
    s = session(tmp_path)
    now = samples(s, 1000, 10)
    s.capture('white', now)
    now = samples(s, 2800, now + 2)
    with pytest.raises(ValueError, match='beyaz'):
        s.capture('black', now)
    s.capture('white', now)
    s.set_mode('manual')
    assert s.white is None


def test_pending_white_expires(tmp_path):
    s = session(tmp_path)
    now = samples(s, 1000, 10)
    s.capture('white', now)
    s._prune(now + 901)
    assert not s.status(None, now + 901)['white_ready']


def test_disk_error_keeps_white_for_retry(tmp_path, monkeypatch):
    s = session(tmp_path)
    now = samples(s, 1000, 10)
    s.capture('white', now)
    now = samples(s, 2800, now + 0.02)

    def fail(*args):
        raise OSError('read only')

    monkeypatch.setattr('ika_line.adc_serial.save_calibration', fail)
    with pytest.raises(OSError, match='read only'):
        s.capture('black', now)
    assert s.white is not None
