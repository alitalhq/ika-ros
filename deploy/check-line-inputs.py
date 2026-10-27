import argparse
import json
from pathlib import Path
import time

import yaml

from ika_hal.gpio import open_chip, resolve_pin

p = argparse.ArgumentParser()
p.add_argument('--seconds', type=float, default=90)
p.add_argument('--config', type=Path,
               default=Path(__file__).with_name('hardware-usb-lidar.yaml'))
a = p.parse_args()
if a.seconds <= 0:
    p.error('--seconds must be positive')
with a.config.open(encoding='utf-8') as config_file:
    config = yaml.safe_load(config_file)
specs = config['line_sensor_node']['ros__parameters']['pins']
pins = [resolve_pin(spec) for spec in specs]
if not pins or len(set(pins)) != len(pins) or None in pins:
    p.error('configuration must contain nonempty, distinct GPIO pins')
requests = {}
try:
    for chip in dict.fromkeys(pin[0] for pin in pins):
        offsets = [pin[1] for pin in pins if pin[0] == chip]
        request = open_chip(chip).request_inputs(
            offsets, consumer='ika_line_probe', bias='as-is')
        requests[chip] = (request, offsets)
    seen = [set() for _ in pins]
    transitions = [0] * len(pins)
    previous = None
    start = time.monotonic()
    print(json.dumps({'probe': 'input-only', 'pins': specs}), flush=True)
    while time.monotonic()-start < a.seconds:
        values = {chip: req.get_all() for chip, (req, _) in requests.items()}
        raw = [values[chip][requests[chip][1].index(offset)]
               for chip, offset in pins]
        for i, value in enumerate(raw):
            seen[i].add(value)
            if previous is not None and previous[i] != value:
                transitions[i] += 1
        if raw != previous:
            print(json.dumps({'seconds': round(time.monotonic()-start, 2),
                              'raw': raw}), flush=True)
        previous = raw
        time.sleep(0.05)
    print(json.dumps({'summary': {'levels_seen': [sorted(s) for s in seen],
                                  'transitions': transitions}}), flush=True)
finally:
    for req, _ in requests.values():
        req.release()
