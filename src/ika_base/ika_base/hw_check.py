"""Saha test aracı: motor yönü, enkoder yönü/çözünürlüğü ve hız ölçümü.

ROS gerektirmez, ika_base_node ile aynı hardware.yaml'ı okur. Robotu
tekerleri havada kalacak şekilde bir kutunun üzerine koyun.

  ros2 run ika_base hw_check pins     --config hardware.yaml
  ros2 run ika_base hw_check motors   --config hardware.yaml [--duty 50] [--seconds 2]
  ros2 run ika_base hw_check encoders --config hardware.yaml
  ros2 run ika_base hw_check sweep    --config hardware.yaml

pins     : dosyadaki her pini ve PWM'i karttaki hatta çözer, çakışmaları bulur.
motors   : her motoru sırayla ileri sürer; tekerin ileri dönüp dönmediğini
           sorar, enkoder işaretine ve ölçülen hıza göre invert önerir.
encoders : motorları sürmez; tekeri elle tam BİR tur ileri çevirin, sayımı
           görün -> encoder.ppr = sayım / çarpan (x4: 4, x2: 2).
sweep    : duty'yi 0'dan artırıp tekerin kalktığı min_duty'yi ve %100'deki
           hızı (max_wheel_speed) ölçer.
Çizgi sensörü için: ros2 run ika_line line_check --config hardware.yaml
"""

import argparse
import math
import sys
import time

import yaml

from ika_base.config import flatten, load_yaml_params
from ika_base.drivetrain import build_drivetrain
from ika_base.encoder import multiplier
from ika_hal.gpio import libgpiod_api, resolve_pin
from ika_hal.pwm import describe_pwm_chips, resolve_pwm

SIDES = ('left', 'right')
SIDE_TR = {'left': 'SOL', 'right': 'SAĞ'}


def _cpr(cfg):
    return cfg['encoder.ppr'] * multiplier(cfg['encoder.mode'])


def _speed(cfg, counts, seconds):
    cpr = _cpr(cfg)
    if cpr <= 0:
        return None
    return counts / cpr * 2.0 * math.pi * cfg['wheel_radius'] / seconds


def _run(dt, side, duty, seconds):
    duties = [duty if side == 'left' else 0.0, duty if side == 'right' else 0.0]
    before = dt.counts() or (0, 0)
    dt.set_duty(*duties)
    time.sleep(seconds)
    dt.set_duty(0.0, 0.0)
    after = dt.counts() or (0, 0)
    time.sleep(0.5)
    return [after[i] - before[i] for i in range(2)]


def cmd_motors(cfg, dt, args):
    for idx, side in enumerate(SIDES):
        input(f'\n[{SIDE_TR[side]}] Enter -> {args.seconds:.1f} sn '
              f'%{args.duty:.0f} ileri sürülecek...')
        delta = _run(dt, side, args.duty, args.seconds)
        answer = input('Teker İLERİ yönde mi döndü? [e/h]: ').strip().lower()
        physical_forward = not answer.startswith('h')
        if not physical_forward:
            print(f'  -> {side}.invert değerini tersine çevirin (şu an {cfg[side + ".invert"]})')
        if dt.counts() is None:
            continue
        other = delta[1 - idx]
        print(f'  enkoder sayımı: {delta[idx]} (diğer teker: {other})')
        if delta[idx] == 0:
            print('  !! sayım yok: enc_a/enc_b pinlerini, besleme ve bias ayarını kontrol edin')
        elif abs(other) > abs(delta[idx]) * 0.5:
            print('  !! diğer teker de sayıyor: sol/sağ enkoder pinleri karışmış olabilir')
        elif (delta[idx] > 0) != physical_forward:
            # Sayım, tekerin gerçek dönüş yönüyle aynı işaretli olmalı.
            current = cfg[f'{side}.enc_invert']
            print(f'  -> {side}.enc_invert değerini tersine çevirin (şu an {current})')
        speed = _speed(cfg, abs(delta[idx]), args.seconds)
        if speed and delta[idx] != 0:
            print(f'  ölçülen hız: {speed:.3f} m/s @ %{args.duty:.0f}')


def cmd_encoders(cfg, dt, args):
    if dt.counts() is None:
        sys.exit('encoder.mode: none, ölçülecek enkoder yok')
    print('Tekeri elle tam bir tur İLERİ çevirin. Çıkmak için Ctrl+C.')
    start = dt.counts()
    mult = multiplier(cfg['encoder.mode'])
    try:
        while True:
            now = dt.counts()
            delta = [now[i] - start[i] for i in range(2)]
            errors = dt.encoder_errors()
            print(f'\r  sol: {delta[0]:7d} (ppr≈{delta[0] / mult:7.1f})   '
                  f'sağ: {delta[1]:7d} (ppr≈{delta[1] / mult:7.1f})   '
                  f'hata: {errors[0]}/{errors[1]}   ', end='', flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()


def cmd_sweep(cfg, dt, args):
    if dt.counts() is None:
        sys.exit('sweep için enkoder gerekli')
    for side in SIDES:
        input(f'\n[{SIDE_TR[side]}] Enter -> duty taraması başlıyor...')
        min_duty = None
        for duty in range(5, 101, 5):
            delta = _run(dt, side, float(duty), 1.0)
            idx = SIDES.index(side)
            speed = _speed(cfg, abs(delta[idx]), 1.0)
            print(f'  %{duty:3d}: {abs(delta[idx]):6d} sayım  {speed:.3f} m/s')
            if min_duty is None and abs(delta[idx]) > 0:
                min_duty = duty
        print(f'  -> pid.min_duty ≈ {min_duty}, max_wheel_speed ≈ {speed:.3f} '
              '(iki tekerin küçüğünü yazın)')


def _sections(path):
    with open(path) as f:
        doc = yaml.safe_load(f) or {}
    return {node: flatten(body.get('ros__parameters', {})) for node, body in doc.items()}


def cmd_pins(path):
    """Donanım açmadan (yalnızca ad çözerek) tüm pinleri listeler."""
    api = libgpiod_api()
    if api == 0:
        sys.exit("libgpiod python bağlaması yok: bu komutu robotta, konteyner içinde çalıştırın")
    print(f'libgpiod python API: v{api}')
    used, problems = {}, []
    for node, params in _sections(path).items():
        for key, value in params.items():
            specs = value if isinstance(value, list) else [value]
            for i, spec in enumerate(specs):
                if not isinstance(spec, str) or not spec.strip():
                    continue
                name = f'{node}.{key}' + (f'[{i}]' if isinstance(value, list) else '')
                if key.split('.')[-1] in ('pwm',):
                    try:
                        chip, channel = resolve_pwm(spec)
                        print(f'  {name:38s} {spec:10s} -> pwmchip{chip}/pwm{channel}')
                    except ValueError as e:
                        problems.append(f'{name}: {e}')
                    continue
                if not (spec.upper().startswith('GPIO') or spec.startswith('gpiochip')):
                    continue
                try:
                    pin = resolve_pin(spec)
                except ValueError as e:
                    problems.append(f'{name}: {e}')
                    continue
                print(f'  {name:38s} {spec:10s} -> {pin[0]}:{pin[1]}')
                if pin in used:
                    problems.append(f'{name} ve {used[pin]} aynı hat: {spec}')
                used[pin] = name
    print('\nPWM çipleri:')
    for row in describe_pwm_chips() or ['  (yok: overlay açık mı? bkz. docs/donanim.md)']:
        print(f'  {row}')
    if problems:
        print('\nSORUNLAR:')
        for problem in problems:
            print(f'  !! {problem}')
        sys.exit(1)
    print('\nTüm pinler çözüldü, çakışma yok.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['pins', 'motors', 'encoders', 'sweep'])
    parser.add_argument('--config', required=True, help='hardware.yaml yolu')
    parser.add_argument('--duty', type=float, default=50.0)
    parser.add_argument('--seconds', type=float, default=2.0)
    args = parser.parse_args(argv)
    if args.command == 'pins':
        return cmd_pins(args.config)

    cfg = load_yaml_params(args.config)
    if args.command == 'sweep' and _cpr(cfg) <= 0:
        sys.exit('önce encoder.ppr ayarlayın (hw_check encoders)')
    dt = build_drivetrain(cfg)
    try:
        {'motors': cmd_motors, 'encoders': cmd_encoders, 'sweep': cmd_sweep}[args.command](
            cfg, dt, args)
    except KeyboardInterrupt:
        print()
    finally:
        dt.set_duty(0.0, 0.0)
        dt.close()


if __name__ == '__main__':
    main()
