import os

import pytest

from ika_hal.lidar import (RateMeter, choose_source, find_usb_port, load_choice, save_choice,
                           sllidar_arguments)


def test_find_usb_port_prefers_first_pattern(tmp_path):
    by_id = tmp_path / 'by-id'
    by_id.mkdir()
    (by_id / 'usb-Silicon_Labs_CP2102_0001-if00-port0').touch()
    (tmp_path / 'ttyUSB0').touch()
    patterns = (str(by_id / '*CP210*'), str(tmp_path / 'ttyUSB*'))
    assert find_usb_port(patterns).endswith('CP2102_0001-if00-port0')
    assert find_usb_port((str(tmp_path / 'yok*'), str(tmp_path / 'ttyUSB*'))).endswith('ttyUSB0')
    assert find_usb_port((str(tmp_path / 'yok*'),)) == ''


def test_choice_roundtrip_and_invalid(tmp_path):
    path = str(tmp_path / 'ika' / 'lidar_source')
    assert load_choice(path) is None
    save_choice(path, 'gpio')
    assert load_choice(path) == 'gpio'
    with open(path, 'w') as f:
        f.write('seri\n')
    assert load_choice(path) is None
    with pytest.raises(ValueError):
        save_choice(path, 'seri')
    assert not os.path.exists(path + '.tmp')


def test_choose_source_precedence():
    assert choose_source('gpio', 'usb', 'usb') == 'gpio'
    assert choose_source('', 'gpio', 'usb') == 'gpio'
    assert choose_source('', None, 'usb') == 'usb'
    with pytest.raises(ValueError):
        choose_source('', None, 'seri')


def test_sllidar_arguments():
    args = sllidar_arguments('/dev/ttyS3', 115200, 'lidar_link', False, True)
    assert args[:3] == ['--ros-args', '-r', '__node:=sllidar_node']
    assert 'serial_port:=/dev/ttyS3' in args
    assert 'serial_baudrate:=115200' in args
    assert 'angle_compensate:=true' in args


def test_rate_meter():
    meter = RateMeter(window=2.0)
    assert meter.rate(0.0) == 0.0
    for i in range(11):
        meter.tick(i * 0.1)
    assert meter.rate(1.0) == pytest.approx(10.0)
    assert meter.rate(5.0) == 0.0
