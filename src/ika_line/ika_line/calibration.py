"""Serial sensor calibration with fresh, stationary surface references."""

import collections
import statistics

from ika_line import adc_serial

WINDOW = 1.0
TIMEOUT = 0.5
WHITE_TTL = 900.0


class CalibrationSession:
    def __init__(self, path):
        self.path = path
        self.mode = None
        self.command_at = float('-inf')
        self.stopped = False
        self.frames = collections.deque()
        self.last_sample_at = float('-inf')
        self.white = None
        self.white_at = float('-inf')
        self.message = ''

    def clear(self):
        self.frames.clear()
        self.white = None

    def set_mode(self, mode):
        self.mode = mode
        if mode != 'idle':
            self.clear()

    def set_command(self, values, now):
        if now - self.command_at > TIMEOUT:
            self.clear()
        self.command_at = now
        self.stopped = all(v == 0.0 for v in values)
        if not self.stopped:
            self.clear()

    def stationary(self, now):
        return self.mode == 'idle' and self.stopped and now - self.command_at < TIMEOUT

    def feed(self, values, now):
        if now - self.last_sample_at > TIMEOUT:
            self.clear()
        self.last_sample_at = now
        if not self.stationary(now):
            self.clear()
            return
        self.frames.append((now, list(values)))
        self._prune(now)

    def _prune(self, now):
        while self.frames and now - self.frames[0][0] > WINDOW:
            self.frames.popleft()
        if now - self.white_at > WHITE_TTL:
            self.white = None

    def ready(self, now):
        self._prune(now)
        return (self.stationary(now) and len(self.frames) >= 10
                and now - self.frames[-1][0] < TIMEOUT
                and self.frames[-1][0] - self.frames[0][0] >= 0.8)

    def capture(self, surface, now):
        if not self.ready(now):
            raise ValueError('Robot Boşta ve hareketsiz olmalı; en az 1 saniye canlı veri bekleyin')
        frames = [v for _, v in self.frames]
        if surface == 'white':
            self.white = frames
            self.white_at = now
            self.frames.clear()  # black must contain only new samples
            self.message = 'Beyaz referans alındı. Şimdi mat siyah yüzeyi yerleştirin.'
            return None
        if self.white is None:
            raise ValueError('Önce beyaz referansı alın (15 dakika geçerli)')
        # Do not accept frames from before the user placed the second surface.
        if self.frames[0][0] <= self.white_at:
            raise ValueError('Siyah yüzeyde en az 1 saniye bekleyin')
        calibration = adc_serial.make_calibration(self.white, frames)
        adc_serial.save_calibration(self.path, calibration)
        self.white = None
        self.message = 'Kalibrasyon kaydedildi; sonraki açılışlarda otomatik yüklenir.'
        return calibration

    def status(self, calibration, now):
        ready = self.ready(now)
        result = {'supported': True, 'ready': ready, 'calibrated': calibration is not None,
                  'white_ready': self.white is not None, 'message': self.message,
                  'samples': len(self.frames)}
        if calibration:
            result.update(calibration)
            result['threshold_mv'] = [(w + b) / 2 for w, b in
                                      zip(calibration['white_mv'], calibration['black_mv'])]
        if self.white:
            result['pending_white_mv'] = [statistics.median(c) for c in zip(*self.white)]
        return result
