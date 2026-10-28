import time

import pytest

from ika_base.encoder import EncoderReader, QuadratureDecoder
from ika_hal.gpio import MockChip

FORWARD = [('a', 1), ('b', 1), ('a', 0), ('b', 0)]


def test_x4_forward_and_backward():
    dec = QuadratureDecoder('x4')
    for _ in range(3):
        for ch, level in FORWARD:
            dec.on_edge(ch, level)
    assert dec.count == 12
    for ch, level in reversed(FORWARD):
        dec.on_edge(ch, 1 - level)
    assert dec.count == 8
    assert dec.errors == 0


def test_x4_invert_and_missed_edge_counts_error():
    dec = QuadratureDecoder('x4', invert=True)
    dec.on_edge('a', 1)          # 00 -> 10: ileri, ters çevrilmiş
    assert dec.count == -1
    dec.on_edge('a', 1)          # aynı seviye tekrar: arada kenar kaçmış
    assert dec.count == -1
    assert dec.errors == 1


def test_x2_uses_sampled_b():
    dec = QuadratureDecoder('x2')
    dec.on_edge('a', 1, other_level=0)   # ileri
    dec.on_edge('a', 0, other_level=1)   # ileri
    assert dec.count == 2
    dec.on_edge('a', 1, other_level=1)   # geri
    assert dec.count == 1


@pytest.mark.parametrize('mode,expected', [('x4', 8), ('x2', 4)])
def test_reader_with_mock_chip(mode, expected):
    chip = MockChip('gpiochip9')
    reader = EncoderReader(lambda name: chip,
                           [(('gpiochip9', 1), ('gpiochip9', 2), False),
                            (('gpiochip9', 3), ('gpiochip9', 4), True)], mode=mode)
    try:
        for _ in range(2):
            for ch, level in FORWARD:
                chip.inject_edge(1 if ch == 'a' else 2, level)
                time.sleep(0.02)   # x2, B'yi A kenarı işlenirken okur
        deadline = time.monotonic() + 2.0
        while reader.counts()[0] != expected and time.monotonic() < deadline:
            time.sleep(0.01)
        assert reader.counts() == [expected, 0]
    finally:
        reader.close()


def test_reader_orders_edges_across_chips():
    # A ve B farklı gpiochip'lerde: olaylar iki ayrı kuyruktan gelir ama
    # zaman sırasıyla işlenmelidir, yoksa hızlı dönüşte sayım bozulur.
    chips = {'gpiochip1': MockChip('gpiochip1'), 'gpiochip2': MockChip('gpiochip2')}
    reader = EncoderReader(chips.__getitem__,
                           [(('gpiochip1', 4), ('gpiochip2', 5), False)])
    try:
        for _ in range(250):
            for ch, level in FORWARD:
                if ch == 'a':
                    chips['gpiochip1'].inject_edge(4, level)
                else:
                    chips['gpiochip2'].inject_edge(5, level)
        deadline = time.monotonic() + 2.0
        while reader.counts()[0] != 1000 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert reader.counts() == [1000]
        assert reader.errors() == [0]
    finally:
        reader.close()


class _PipeLines:
    """libgpiod v2 isteği gibi fd veren sahte olay kuyruğu (select yolu için)."""

    def __init__(self):
        import os
        from collections import deque
        self._r, self._w = os.pipe()
        self.queue = deque()
        self.levels = {}

    def push(self, offset, level):
        import os
        from ika_hal.gpio import Edge
        self.levels[offset] = level
        self.queue.append(Edge(offset, level, time.monotonic_ns()))
        os.write(self._w, b'x')

    def fileno(self):
        return self._r

    def wait(self, timeout_s):
        return bool(self.queue)

    def read(self):
        import os
        edges = list(self.queue)
        self.queue.clear()
        os.read(self._r, 4096)
        return edges

    def get(self, offset):
        return self.levels.get(offset, 0)

    def release(self):
        import os
        os.close(self._r)
        os.close(self._w)


class _PipeChip:
    def __init__(self):
        self.lines = _PipeLines()

    def request_edges(self, offsets, bias='as-is'):
        return self.lines


def test_reader_orders_edges_across_chips_with_select():
    chips = {'gpiochip1': _PipeChip(), 'gpiochip2': _PipeChip()}
    reader = EncoderReader(chips.__getitem__, [(('gpiochip1', 4), ('gpiochip2', 5), False)])
    try:
        for _ in range(250):
            for ch, level in FORWARD:
                if ch == 'a':
                    chips['gpiochip1'].lines.push(4, level)
                else:
                    chips['gpiochip2'].lines.push(5, level)
        deadline = time.monotonic() + 2.0
        while reader.counts()[0] != 1000 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert reader.counts() == [1000]
        assert reader.errors() == [0]
    finally:
        reader.close()
