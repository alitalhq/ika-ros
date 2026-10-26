"""libgpiod v1 / v2 ve donanımsız (mock) arka uçlar için ince GPIO katmanı.

Docker imajı PyPI'den libgpiod v2 bağlamasını kurar (bkz. docker/Dockerfile);
v2 kernel'den sıralı tek olay kuyruğu ve büyük olay tamponu verir, enkoder
okumak için gereklidir. Ubuntu 24.04 apt paketi (v1.6) da çalışır ama yüksek
devirde enkoder olayı kaçırabilir. Üst katmanlar sürüm farkını bilmez:

    pin = resolve_pin('GPIO22')                # -> ('gpiochip2', 41)
    chip = open_chip(pin[0])                   # backend='mock' -> donanımsız
    out = chip.request_outputs([41])           # out.set(41, 1)
    inp = chip.request_inputs([5, 6])          # inp.get_all() -> [0, 1]
    ev = chip.request_edges([1, 2])            # ev.wait(0.1); ev.read() -> [Edge]
    rc = chip.request_flex([3, 4])             # rc.drive_high(); rc.to_input()

Pin yazımı:
    "GPIO22"        Gemstone hat adı (gpiofind ile aynı); önerilen
    "gpiochip2:41"  chip + line offset; ad bulunamazsa
"""

from collections import deque
from dataclasses import dataclass
import glob
import re
import threading
import time

try:
    import gpiod
except ImportError:  # geliştirme makinesi / CI
    gpiod = None

CONSUMER = 'ika'
BIAS_OPTIONS = ('as-is', 'pull-up', 'pull-down', 'disabled')
EVENT_BUFFER_SIZE = 1024        # kernel üst sınırı (16 * 64 hat)
MOCK_CHIP = 'gpiochip-mock'

_NUMERIC = re.compile(r'^(gpiochip\d+|/dev/gpiochip\d+|' + MOCK_CHIP + r'):(\d+)$')
_GPIO_NAME = re.compile(r'^GPIO[-_]?(\d+)$', re.IGNORECASE)


@dataclass(frozen=True)
class Edge:
    offset: int
    level: int          # kenardan sonraki seviye: 1 = yükselen, 0 = düşen
    timestamp_ns: int


def libgpiod_api() -> int:
    """Kurulu python libgpiod API sürümü: 0 (yok), 1 veya 2."""
    if gpiod is None:
        return 0
    return 2 if hasattr(gpiod, 'request_lines') else 1


def _name_candidates(name: str):
    match = _GPIO_NAME.match(name)
    if not match:
        return [name]
    n = match.group(1)
    return list(dict.fromkeys([f'GPIO{n}', f'GPIO-{n}', f'GPIO_{n}', name]))


def resolve_pin(spec: str, backend: str = 'gpiod'):
    """Pin yazımını (chip_adı, line_offset) çiftine çevirir; boş -> None."""
    spec = (spec or '').strip()
    if not spec:
        return None
    numeric = _NUMERIC.match(spec)
    if numeric:
        return numeric.group(1).replace('/dev/', ''), int(numeric.group(2))
    if backend == 'mock':
        match = _GPIO_NAME.match(spec)
        if not match:
            raise ValueError(f"pin '{spec}' geçersiz; 'GPIO22' veya 'gpiochipN:line' yazın")
        return MOCK_CHIP, int(match.group(1))

    candidates = _name_candidates(spec)
    api = libgpiod_api()
    if api == 1:
        for name in candidates:
            line = gpiod.find_line(name)
            if line is not None:
                return line.owner().name(), line.offset()
    elif api == 2:
        for path in sorted(glob.glob('/dev/gpiochip*')):
            with gpiod.Chip(path) as chip:
                for name in candidates:
                    try:
                        return path.replace('/dev/', ''), chip.line_offset_from_id(name)
                    except (OSError, ValueError):
                        continue
    else:
        _missing_libgpiod()
    raise ValueError(
        f"'{spec}' adlı GPIO hattı bulunamadı (denenen: {', '.join(candidates)}). "
        "`gpioinfo` çıktısındaki adı veya 'gpiochipN:line' yazın.")


def open_chip(name: str, backend: str = 'gpiod'):
    if backend == 'mock' or name == MOCK_CHIP:
        return MockChip(name)
    if backend != 'gpiod':
        raise ValueError(f"bilinmeyen GPIO arka ucu: {backend!r} (gpiod | mock)")
    api = libgpiod_api()
    if api == 0:
        _missing_libgpiod()
    return _ChipV2(name) if api == 2 else _ChipV1(name)


def _missing_libgpiod():
    raise RuntimeError(
        "libgpiod python bağlaması yok (pip install 'gpiod>=2.2' ya da "
        "apt install python3-libgpiod); donanımsız denemek için backend:=mock")


def _check_bias(bias: str):
    if bias not in BIAS_OPTIONS:
        raise ValueError(f'bias {BIAS_OPTIONS} değerlerinden biri olmalı, gelen: {bias!r}')


# --- libgpiod 1.x -----------------------------------------------------------

class _ChipV1:

    def __init__(self, name: str):
        self._chip = gpiod.Chip(name)

    def _flags(self, bias: str) -> int:
        _check_bias(bias)
        name = {
            'pull-up': 'LINE_REQ_FLAG_BIAS_PULL_UP',
            'pull-down': 'LINE_REQ_FLAG_BIAS_PULL_DOWN',
            'disabled': 'LINE_REQ_FLAG_BIAS_DISABLE',
        }.get(bias)
        return getattr(gpiod, name, 0) if name else 0

    def _request(self, offsets, consumer, req_type, flags=0, default=None):
        lines = self._chip.get_lines(list(offsets))
        kwargs = {'consumer': consumer, 'type': req_type, 'flags': flags}
        if default is not None:
            kwargs['default_vals'] = [default] * len(offsets)
        lines.request(**kwargs)
        return _LinesV1(lines)

    def request_outputs(self, offsets, consumer=CONSUMER):
        return self._request(offsets, consumer, gpiod.LINE_REQ_DIR_OUT, default=0)

    def request_inputs(self, offsets, consumer=CONSUMER, bias='as-is'):
        return self._request(offsets, consumer, gpiod.LINE_REQ_DIR_IN, self._flags(bias))

    def request_edges(self, offsets, consumer=CONSUMER, bias='as-is'):
        # v1 kernel arabirimi hat başına yalnızca 16 olay tamponlar.
        return self._request(offsets, consumer, gpiod.LINE_REQ_EV_BOTH_EDGES, self._flags(bias))

    def request_flex(self, offsets, consumer=CONSUMER):
        return self._request(offsets, consumer, gpiod.LINE_REQ_DIR_IN)

    def close(self):
        self._chip.close()


class _LinesV1:

    def __init__(self, bulk):
        self._bulk = bulk
        self._lines = bulk.to_list()
        self._by_offset = {line.offset(): line for line in self._lines}
        self._ready = None

    def set(self, offset: int, value: int):
        self._by_offset[offset].set_value(1 if value else 0)

    def get(self, offset: int) -> int:
        return self._by_offset[offset].get_value()

    def get_all(self) -> list:
        return list(self._bulk.get_values())

    def drive_high(self):
        self._bulk.set_direction_output([1] * len(self._lines))

    def to_input(self):
        self._bulk.set_direction_input()

    def wait(self, timeout_s: float) -> bool:
        sec = int(timeout_s)
        self._ready = self._bulk.event_wait(sec=sec, nsec=int((timeout_s - sec) * 1e9))
        return self._ready is not None

    def read(self) -> list:
        ready, self._ready = self._ready, None
        if ready is None:
            return []
        edges = []
        for line in ready.to_list():
            for ev in line.event_read_multiple():
                edges.append(Edge(
                    offset=ev.source.offset(),
                    level=1 if ev.type == gpiod.LineEvent.RISING_EDGE else 0,
                    timestamp_ns=ev.sec * 1_000_000_000 + ev.nsec))
        # Hatlar ayrı tamponlardan okunuyor; zaman sırasına diz.
        edges.sort(key=lambda e: e.timestamp_ns)
        return edges

    def release(self):
        self._bulk.release()


# --- libgpiod 2.x -----------------------------------------------------------

class _ChipV2:

    def __init__(self, name: str):
        self._path = name if name.startswith('/dev/') else f'/dev/{name}'
        if not gpiod.is_gpiochip_device(self._path):
            raise OSError(f'{self._path} bir GPIO chip aygıtı değil')

    @staticmethod
    def _bias(bias: str):
        from gpiod.line import Bias
        _check_bias(bias)
        return {
            'as-is': Bias.AS_IS, 'pull-up': Bias.PULL_UP,
            'pull-down': Bias.PULL_DOWN, 'disabled': Bias.DISABLED,
        }[bias]

    def _request(self, offsets, consumer, settings, **kwargs):
        req = gpiod.request_lines(self._path, consumer=consumer,
                                  config={tuple(offsets): settings}, **kwargs)
        return _LinesV2(req, list(offsets))

    def request_outputs(self, offsets, consumer=CONSUMER):
        from gpiod.line import Direction, Value
        return self._request(offsets, consumer, gpiod.LineSettings(
            direction=Direction.OUTPUT, output_value=Value.INACTIVE))

    def request_inputs(self, offsets, consumer=CONSUMER, bias='as-is'):
        from gpiod.line import Direction
        return self._request(offsets, consumer, gpiod.LineSettings(
            direction=Direction.INPUT, bias=self._bias(bias)))

    def request_edges(self, offsets, consumer=CONSUMER, bias='as-is'):
        from gpiod.line import Direction, Edge as GpiodEdge
        return self._request(offsets, consumer, gpiod.LineSettings(
            direction=Direction.INPUT, edge_detection=GpiodEdge.BOTH,
            bias=self._bias(bias)), event_buffer_size=EVENT_BUFFER_SIZE)

    def request_flex(self, offsets, consumer=CONSUMER):
        from gpiod.line import Direction
        return self._request(offsets, consumer, gpiod.LineSettings(direction=Direction.INPUT))

    def close(self):
        pass


class _LinesV2:

    def __init__(self, req, offsets):
        from gpiod.line import Direction, Value
        self._req = req
        self._offsets = offsets
        self._active = Value.ACTIVE
        self._inactive = Value.INACTIVE
        key = tuple(offsets)
        self._as_output = {key: gpiod.LineSettings(
            direction=Direction.OUTPUT, output_value=Value.ACTIVE)}
        self._as_input = {key: gpiod.LineSettings(direction=Direction.INPUT)}

    def set(self, offset: int, value: int):
        self._req.set_value(offset, self._active if value else self._inactive)

    def get(self, offset: int) -> int:
        return 1 if self._req.get_value(offset) == self._active else 0

    def get_all(self) -> list:
        return [1 if v == self._active else 0 for v in self._req.get_values(self._offsets)]

    def drive_high(self):
        self._req.reconfigure_lines(self._as_output)

    def to_input(self):
        self._req.reconfigure_lines(self._as_input)

    def wait(self, timeout_s: float) -> bool:
        return self._req.wait_edge_events(timeout_s)

    def read(self) -> list:
        rising = gpiod.EdgeEvent.Type.RISING_EDGE
        return [
            Edge(offset=ev.line_offset, level=1 if ev.event_type == rising else 0,
                 timestamp_ns=ev.timestamp_ns)
            for ev in self._req.read_edge_events()
        ]

    def release(self):
        self._req.release()


# --- Donanımsız (mock) arka uç ------------------------------------------------

class MockChip:
    """Bellekte çalışan sahte chip. Testler `inject_edge` / `set_level` ile
    giriş üretebilir, çıkışlar `levels` sözlüğünden okunabilir."""

    def __init__(self, name: str = MOCK_CHIP):
        self.name = name
        self.levels = {}
        self._edge_queues = []
        self._lock = threading.Lock()

    def request_outputs(self, offsets, consumer=CONSUMER):
        for o in offsets:
            self.levels[o] = 0
        return _MockLines(self, offsets)

    def request_inputs(self, offsets, consumer=CONSUMER, bias='as-is'):
        _check_bias(bias)
        for o in offsets:
            self.levels.setdefault(o, 0)
        return _MockLines(self, offsets)

    def request_edges(self, offsets, consumer=CONSUMER, bias='as-is'):
        lines = self.request_inputs(offsets, consumer, bias)
        self._edge_queues.append((set(offsets), lines.queue))
        return lines

    def request_flex(self, offsets, consumer=CONSUMER):
        return self.request_inputs(offsets, consumer)

    def set_level(self, offset: int, level: int):
        self.levels[offset] = level

    def inject_edge(self, offset: int, level: int):
        with self._lock:
            self.levels[offset] = level
            for offsets, queue in self._edge_queues:
                if offset in offsets:
                    queue.append(Edge(offset, level, time.monotonic_ns()))

    def close(self):
        pass


class _MockLines:

    def __init__(self, chip: MockChip, offsets):
        self._chip = chip
        self._offsets = list(offsets)
        self.queue = deque()

    def set(self, offset: int, value: int):
        self._chip.levels[offset] = 1 if value else 0

    def get(self, offset: int) -> int:
        return self._chip.levels.get(offset, 0)

    def get_all(self) -> list:
        return [self.get(o) for o in self._offsets]

    def drive_high(self):
        pass

    def to_input(self):
        pass

    def wait(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while not self.queue and time.monotonic() < deadline:
            time.sleep(0.002)
        return bool(self.queue)

    def read(self) -> list:
        edges = []
        while self.queue:
            edges.append(self.queue.popleft())
        return edges

    def release(self):
        pass
