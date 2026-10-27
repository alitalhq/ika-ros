from ika_line.qtr import dark_channels, read_decay_us


class FakeQtr:
    """Her kanal kendi boşalma süresinde LOW'a düşer; zaman sahte saatten."""

    def __init__(self, decay_us):
        self.decay_us = decay_us
        self.now_ns = 0
        self.released_at = None
        self.calls = []

    def clock(self):
        self.now_ns += 20_000          # her saat okuması 20 µs ilerletir
        return self.now_ns

    def drive_high(self):
        self.calls.append('high')

    def to_input(self):
        self.calls.append('input')
        self.released_at = self.now_ns

    def get_all(self):
        elapsed_us = (self.now_ns - self.released_at) / 1000
        return [0 if elapsed_us >= d else 1 for d in self.decay_us]


def test_decay_times_and_timeout():
    qtr = FakeQtr([100, 1500, 99999])
    times = read_decay_us(qtr, 3, timeout_us=2500, clock=qtr.clock)
    assert qtr.calls == ['high', 'input']
    # Ölçüm çözünürlüğü bir saat okuması (sahte saatte 20 µs).
    assert abs(times[0] - 100) <= 40
    assert abs(times[1] - 1500) <= 40
    assert times[2] == 2500


def test_dark_channels():
    assert dark_channels([120, 1800, 2500], 1000) == [False, True, True]
