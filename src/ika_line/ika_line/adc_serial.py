"""Deneyap Kart'tan (firmware/deneyap_line) gelen analog çizgi sensörü verisi.

Kart her kanalı ADC ile milivolt olarak okur ve satır başına bir JSON çerçeve
gönderir:  {"ika_adc":1,"seq":<sayaç>,"mv":[D1, ..., D8]}

Kanal başına beyaz ve siyah zemin ölçümünden (kalibrasyon) eşik çıkarılır:
eşik iki medyanın ortası, siyahın hangi tarafta olduğu kanal kanal belirlenir.
"""

import json
import os
import statistics

CHANNELS = 8
MAX_MV = 3600
MIN_SEPARATION_MV = 100   # beyaz/siyah medyanları arasında en az bu kadar fark


def parse_frame(line):
    """Döner: (seq, [mv] * 8). Geçersiz çerçevede ValueError."""
    if len(line) > 512:
        raise ValueError('çerçeve çok uzun')
    data = json.loads(line)
    if not isinstance(data, dict) or data.get('ika_adc') != 1:
        raise ValueError('ika_adc çerçevesi değil')
    seq, values = data.get('seq'), data.get('mv')
    if type(seq) is not int or not 0 <= seq <= 0xffffffff:
        raise ValueError('geçersiz seq')
    if not isinstance(values, list) or len(values) != CHANNELS:
        raise ValueError(f'{CHANNELS} kanal gerekli')
    if any(type(v) is not int or not 0 <= v <= MAX_MV for v in values):
        raise ValueError('geçersiz milivolt değeri')
    return seq, values


class FrameReader:
    """Seri porttan gelen baytları satırlara böler; son geçerli çerçeveyi verir."""

    def __init__(self):
        self.buffer = b''
        self.last_seq = None

    def feed(self, data):
        """Döner: bu baytlarla tamamlanan en yeni çerçevenin değerleri veya None."""
        self.buffer += data
        if len(self.buffer) > 8192:      # satır sonu hiç gelmiyorsa (yanlış baud)
            self.buffer = b''
        latest = None
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            try:
                seq, values = parse_frame(line)
            except (ValueError, UnicodeError):
                continue
            if seq == self.last_seq:
                continue
            self.last_seq = seq
            latest = values
        return latest


def make_calibration(white_frames, black_frames):
    """Beyaz ve siyah zeminde toplanan çerçevelerden kanal başına eşik.
    Kanallar ayrışmıyorsa ValueError (hangi kanal olduğu mesajda)."""
    if not white_frames or not black_frames:
        raise ValueError('beyaz ve siyah ölçüm gerekli')
    white = [statistics.median(c) for c in zip(*white_frames)]
    black = [statistics.median(c) for c in zip(*black_frames)]
    white_range = [(min(c), max(c)) for c in zip(*white_frames)]
    black_range = [(min(c), max(c)) for c in zip(*black_frames)]
    for i, (w, b) in enumerate(zip(white, black)):
        if abs(w - b) < MIN_SEPARATION_MV:
            raise ValueError(f'D{i + 1}: beyaz {w:.0f} mV, siyah {b:.0f} mV; '
                             f'fark {MIN_SEPARATION_MV} mV altında')
        overlap = (white_range[i][1] >= black_range[i][0] if b > w
                   else black_range[i][1] >= white_range[i][0])
        if overlap:
            raise ValueError(f'D{i + 1}: beyaz ve siyah ölçümler örtüşüyor')
    return {'white_mv': white, 'black_mv': black}


def validate_calibration(data):
    for name in ('white_mv', 'black_mv'):
        values = data.get(name) if isinstance(data, dict) else None
        if not isinstance(values, list) or len(values) != CHANNELS:
            raise ValueError(f'{name}: {CHANNELS} değer gerekli')
        if any(type(v) not in (int, float) or not 0 <= v <= MAX_MV for v in values):
            raise ValueError(f'{name}: geçersiz değer')
    if any(abs(w - b) < MIN_SEPARATION_MV
           for w, b in zip(data['white_mv'], data['black_mv'])):
        raise ValueError(f'her kanalda en az {MIN_SEPARATION_MV} mV fark gerekli')
    return data


def load_calibration(path):
    """Dosya yoksa None; bozuksa ValueError/OSError."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return validate_calibration(json.load(f))


def save_calibration(path, calibration):
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(calibration, f, indent=2)
    os.replace(tmp, path)


def dark_channels(values, calibration):
    """Siyah zemine benzeyen kanallar. Kalibrasyon yoksa hiçbiri."""
    if calibration is None:
        return [False] * len(values)
    return [v > (w + b) / 2 if b > w else v < (w + b) / 2
            for v, w, b in zip(values, calibration['white_mv'], calibration['black_mv'])]
