import json

import pytest

from ika_line import adc_serial


def frame(seq, mv):
    return json.dumps({'ika_adc': 1, 'seq': seq, 'mv': mv}).encode() + b'\n'


def test_parse_frame():
    assert adc_serial.parse_frame(frame(3, [100] * 8)) == (3, [100] * 8)


@pytest.mark.parametrize('mv', [[1] * 7, [1] * 9, [True] * 8, [-1] * 8, [4000] * 8, [1.5] * 8])
def test_parse_frame_rejects_bad_values(mv):
    with pytest.raises(ValueError):
        adc_serial.parse_frame(frame(1, mv))


@pytest.mark.parametrize('line', [b'null', b'[]', b'{}', b'{', b'{"ika_adc":2,"seq":1,"mv":[]}'])
def test_parse_frame_rejects_other_lines(line):
    with pytest.raises(ValueError):
        adc_serial.parse_frame(line)


def test_reader_splits_partial_lines_and_skips_noise():
    reader = adc_serial.FrameReader()
    data = b'boot garbage\n' + frame(1, [10] * 8) + frame(2, [20] * 8)
    assert reader.feed(data[:20]) is None
    assert reader.feed(data[20:]) == [20] * 8


def test_reader_drops_repeated_sequence():
    reader = adc_serial.FrameReader()
    assert reader.feed(frame(5, [10] * 8)) == [10] * 8
    assert reader.feed(frame(5, [10] * 8)) is None


def test_reader_recovers_from_unterminated_stream():
    reader = adc_serial.FrameReader()
    reader.feed(b'x' * 9000)
    assert reader.feed(frame(1, [1] * 8)) == [1] * 8


def test_calibration_and_classification_both_polarities():
    white = [[3000, 200] * 4, [2980, 220] * 4]
    black = [[3090, 2500] * 4, [3100, 2600] * 4]
    cal = adc_serial.make_calibration(white, black)
    assert adc_serial.dark_channels([3095, 2550] * 4, cal) == [True] * 8
    assert adc_serial.dark_channels([2990, 210] * 4, cal) == [False] * 8


def test_calibration_rejects_close_or_overlapping_channels():
    with pytest.raises(ValueError, match='D1'):
        adc_serial.make_calibration([[3000] * 8], [[3050] + [3200] * 7])
    with pytest.raises(ValueError, match='örtüşüyor'):
        adc_serial.make_calibration([[1000] * 8, [1000] * 8, [1500] * 8],
                                    [[1400] * 8, [1200] * 8, [1200] * 8])


def test_no_detection_without_calibration():
    assert adc_serial.dark_channels([3000] * 8, None) == [False] * 8


def test_calibration_file_round_trip(tmp_path):
    path = str(tmp_path / 'sub' / 'cal.json')
    assert adc_serial.load_calibration(path) is None
    cal = {'white_mv': [100.0] * 8, 'black_mv': [3000.0] * 8}
    adc_serial.save_calibration(path, cal)
    assert adc_serial.load_calibration(path) == cal


def test_calibration_file_validation(tmp_path):
    path = tmp_path / 'cal.json'
    path.write_text(json.dumps({'white_mv': [2000] * 8, 'black_mv': [2050] * 8}))
    with pytest.raises(ValueError):
        adc_serial.load_calibration(str(path))
