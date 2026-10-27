"""Pololu QTR-xRC (RC tipi) yansıma sensörü okuma.

Her kanal bir kapasitör + fototransistördür:
  1. hat HIGH sürülür, kapasitör `charge_us` boyunca şarj olur
  2. hat girişe çevrilir; fototransistör kapasitörü boşaltır
  3. hattın LOW'a düşme süresi ölçülür: beyaz (çok yansıma) kısa,
     siyah (az yansıma) uzun; `timeout_us`'u aşan kanal timeout sayılır
Kanallar birlikte ölçülür; tek okuma en fazla timeout_us sürer.
"""

import time


def read_decay_us(lines, count: int, timeout_us: int = 2500, charge_us: int = 10,
                  clock=time.perf_counter_ns):
    """lines: drive_high() / to_input() / get_all() sağlayan istek nesnesi.
    Döner: kanal başına boşalma süresi [µs], en fazla timeout_us."""
    lines.drive_high()
    end_charge = clock() + charge_us * 1000
    while clock() < end_charge:
        pass
    lines.to_input()
    start = clock()
    times = [timeout_us] * count
    pending = set(range(count))
    while pending:
        elapsed = (clock() - start) // 1000
        if elapsed >= timeout_us:
            break
        values = lines.get_all()
        for i in [i for i in pending if not values[i]]:
            times[i] = int(elapsed)
            pending.discard(i)
    return times


def dark_channels(times, threshold_us: int):
    """Süresi eşikten uzun kanallar koyu zemin görüyordur."""
    return [t >= threshold_us for t in times]
