"""Çizgi sensörünü ROS olmadan canlı okur: kanal sırası ve QTR eşik ayarı.

  ros2 run ika_line line_check --config hardware.yaml

Sensörü önce zeminin, sonra çizginin üzerinden soldan sağa geçirin:
değerler soldan sağa sırayla değişmeli. QTR'de zemin ve çizgi değerlerinin
arasında kalan bir `qtr.threshold_us` seçin.
"""

import argparse
import sys
import time

import yaml

from ika_hal.gpio import resolve_pin
from ika_line.line_sensor_node import PinGroup
from ika_line.qtr import read_decay_us


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config', required=True, help='hardware.yaml yolu')
    args = parser.parse_args(argv)

    with open(args.config) as f:
        params = (yaml.safe_load(f) or {}).get('line_sensor_node', {}).get('ros__parameters', {})
    pins = [resolve_pin(s) for s in params.get('pins', []) if s.strip()]
    if not pins:
        sys.exit('line_sensor_node.pins boş')
    qtr = params.get('type', 'qtr_rc') == 'qtr_rc'
    qtr_cfg = params.get('qtr', {})
    threshold = qtr_cfg.get('threshold_us', 1000)
    timeout = qtr_cfg.get('timeout_us', 2500)
    group = PinGroup(pins, 'gpiod', 'flex' if qtr else 'input',
                     params.get('digital', {}).get('bias', 'as-is'))

    print('soldan sağa ' + ('boşalma süresi [µs], * = eşik üstü (koyu)' if qtr else 'seviye'))
    print('Ctrl+C ile çıkın.')
    try:
        while True:
            if qtr:
                raw = read_decay_us(group, len(pins), timeout)
                cells = [f'{t:5d}{"*" if t >= threshold else " "}' for t in raw]
            else:
                cells = [f'{v:3d}' for v in group.get_all()]
            print('\r  ' + ' '.join(cells), end='', flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
    finally:
        group.release()


if __name__ == '__main__':
    main()
