"""line_sensor_node: çizgi sensörü dizisini GPIO'dan veya Deneyap Kart'tan okur.

type: serial   Analog sensör Deneyap Kart'ın ADC'sine bağlı; kart milivoltları
               UART'tan gönderir (firmware/deneyap_line). Kanal başına eşik
               kalibrasyondan gelir; kalibrasyon yoksa hiçbir kanal çizgi görmez.
type: qtr_rc   Pololu QTR-8RC / QTR-xRC (RC tipi, kanal başına 1 GPIO).
               `qtr.threshold_us` üstündeki boşalma süresi = koyu zemin.
type: digital  TCRT5000 vb. modüllerin dijital (DO) çıkışı;
               `line_level` = sensör çizgiyi görünce okunan seviye.

`pins` soldan sağa sıralanır (robotun arkasından, ileri bakarak). 3.3 V lojik!
Yayın   : /line/state (ika_interfaces/LineState; serial'de raw = mV)
Servisler (yalnız serial; sensör ~1 sn zeminde dururken çağrılır):
  /line/calibrate_white, /line/calibrate_black  (std_srvs/Trigger)
  Siyah ölçümü beyazdan sonra alınır, ikisi ayrışırsa kalibrasyon kaydedilir.
"""

import collections
import os
import time

import rclpy
from rclpy.node import Node

from std_srvs.srv import Trigger

from ika_hal.gpio import open_chip, resolve_pin
from ika_interfaces.msg import LineState
from ika_line import adc_serial
from ika_line.line_math import read_line, sensor_positions
from ika_line.qtr import dark_channels, read_decay_us

SERIAL_TIMEOUT = 0.5      # bu süre çerçeve gelmezse yayın durur (takip komutu da kesilir)
CALIBRATION_WINDOW = 1.0  # kalibrasyonda kullanılan son ölçümler [s]


class PinGroup:
    """Farklı GPIO chip'lerine dağılmış pinleri sırası korunarak tek grup
    gibi kullanır (chip başına tek istek)."""

    def __init__(self, pins, backend, mode, bias='as-is'):
        self._requests = []
        self._index = []          # her pin için (istek sırası, istek içindeki sıra)
        by_chip = {}
        for chip_name, offset in pins:
            by_chip.setdefault(chip_name, []).append(offset)
        positions = {}
        for chip_name, offsets in by_chip.items():
            chip = open_chip(chip_name, backend)
            if mode == 'flex':
                req = chip.request_flex(offsets, consumer='ika_line')
            else:
                req = chip.request_inputs(offsets, consumer='ika_line', bias=bias)
            for j, offset in enumerate(offsets):
                positions[(chip_name, offset)] = (len(self._requests), j)
            self._requests.append(req)
        self._index = [positions[pin] for pin in pins]

    def drive_high(self):
        for req in self._requests:
            req.drive_high()

    def to_input(self):
        for req in self._requests:
            req.to_input()

    def get_all(self):
        values = [req.get_all() for req in self._requests]
        return [values[r][j] for r, j in self._index]

    def release(self):
        for req in self._requests:
            req.release()


class LineSensorNode(Node):

    def __init__(self):
        super().__init__('line_sensor_node')
        self.declare_parameter('backend', 'gpiod')
        self.declare_parameter('type', 'qtr_rc')
        self.declare_parameter('pins', [''])
        self.declare_parameter('emitter_pin', '')
        self.declare_parameter('spacing', 0.009525)
        self.declare_parameter('rate', 100.0)
        self.declare_parameter('frame_id', 'line_sensor_link')
        self.declare_parameter('line_is_dark', True)
        self.declare_parameter('qtr.threshold_us', 1000)
        self.declare_parameter('qtr.timeout_us', 2500)
        self.declare_parameter('qtr.charge_us', 10)
        self.declare_parameter('digital.line_level', 1)
        self.declare_parameter('digital.bias', 'as-is')
        self.declare_parameter('serial.port', '/dev/ttyS3')
        self.declare_parameter('serial.baudrate', 115200)
        self.declare_parameter('serial.calibration', '~/.ika/line_calibration.json')

        p = lambda name: self.get_parameter(name).value  # noqa: E731
        backend = p('backend')
        self.type = p('type')
        if self.type not in ('serial', 'qtr_rc', 'digital'):
            raise ValueError(f"type serial, qtr_rc veya digital olmalı, gelen: {self.type!r}")
        self.frame_id = p('frame_id')
        self.pub = self.create_publisher(LineState, 'line/state', 10)
        if self.type == 'serial':
            self._init_serial(p)
            return

        pins = [resolve_pin(s, backend) for s in p('pins') if s.strip()]
        if not pins and backend == 'mock':
            pins = [resolve_pin(f'GPIO{100 + i}', 'mock') for i in range(8)]
        if not pins:
            raise ValueError("line_sensor_node: 'pins' boş (ör. ['GPIO6', 'GPIO19', ...])")

        self.count = len(pins)
        self.positions = sensor_positions(self.count, p('spacing'))
        self.line_is_dark = p('line_is_dark')
        self.threshold = p('qtr.threshold_us')
        self.timeout = p('qtr.timeout_us')
        self.charge = p('qtr.charge_us')
        self.line_level = p('digital.line_level')
        self.group = PinGroup(pins, backend, 'flex' if self.type == 'qtr_rc' else 'input',
                              p('digital.bias'))

        self.emitter = None
        emitter = resolve_pin(p('emitter_pin'), backend)
        if emitter:
            self.emitter = open_chip(emitter[0], backend).request_outputs(
                [emitter[1]], consumer='ika_line')
            self.emitter.set(emitter[1], 1)

        self.create_timer(1.0 / p('rate'), self._tick)
        self.get_logger().info(
            f'{self.type}: {self.count} kanal, aralık {p("spacing") * 1000:.1f} mm'
            + (f', eşik {self.threshold} µs' if self.type == 'qtr_rc' else ''))

    # --- type: serial (Deneyap Kart) ---
    def _init_serial(self, p):
        self.group = None
        self.emitter = None
        self.count = adc_serial.CHANNELS
        self.positions = sensor_positions(self.count, p('spacing'))
        self.port_name = p('serial.port')
        self.baudrate = p('serial.baudrate')
        self.calibration_path = os.path.expanduser(p('serial.calibration'))
        self.calibration_stamp = None
        self.calibration = None
        self.port = None
        self.reader = adc_serial.FrameReader()
        self.last_frame = time.monotonic()
        self.recent = collections.deque()          # (zaman, mv) son CALIBRATION_WINDOW
        self.white_frames = None
        self.warned = set()
        self._load_calibration()
        self.create_service(Trigger, 'line/calibrate_white', self._srv_white)
        self.create_service(Trigger, 'line/calibrate_black', self._srv_black)
        self.create_timer(1.0 / p('rate'), self._tick_serial)
        self.get_logger().info(
            f'serial: Deneyap {self.port_name} @ {self.baudrate}, kalibrasyon '
            + ('var' if self.calibration else f'YOK ({self.calibration_path})'))

    def _warn_once(self, key, text):
        if key not in self.warned:
            self.warned.add(key)
            self.get_logger().warn(text)

    def _load_calibration(self):
        """Dosya değiştiyse yeniden okur (elle kopyalanan kalibrasyon da geçerli olur)."""
        try:
            stamp = os.stat(self.calibration_path).st_mtime_ns
        except OSError:
            stamp = None
        if stamp == self.calibration_stamp:
            return
        self.calibration_stamp = stamp
        try:
            self.calibration = adc_serial.load_calibration(self.calibration_path)
        except (OSError, ValueError) as exc:
            self.calibration = None
            self.get_logger().error(f'kalibrasyon dosyası geçersiz: {exc}')

    def _open_port(self):
        import serial   # yalnız serial tipinde gerekli (python3-serial)
        try:
            self.port = serial.Serial(self.port_name, self.baudrate, timeout=0)
            self.port.reset_input_buffer()
            self.reader = adc_serial.FrameReader()
            self.last_frame = time.monotonic()
            self.warned.discard('port')
            self.get_logger().info(f'{self.port_name} açıldı')
        except (serial.SerialException, OSError) as exc:
            self.port = None
            self._warn_once('port', f'{self.port_name} açılamadı: {exc}')

    def _tick_serial(self):
        if self.port is None:
            self._open_port()
            if self.port is None:
                return
        try:
            waiting = self.port.in_waiting
            values = self.reader.feed(self.port.read(waiting)) if waiting else None
        except OSError as exc:
            self.get_logger().error(f'{self.port_name} okunamadı: {exc}')
            self.port.close()
            self.port = None
            return
        now = time.monotonic()
        if values is None:
            if now - self.last_frame > SERIAL_TIMEOUT:
                self._warn_once('timeout', "Deneyap'tan veri gelmiyor (kablo, baud, firmware)")
            return
        self.last_frame = now
        self.warned.discard('timeout')
        self.recent.append((now, values))
        while self.recent and now - self.recent[0][0] > CALIBRATION_WINDOW:
            self.recent.popleft()
        self._load_calibration()
        if self.calibration is None:
            self._warn_once('calibration', 'çizgi sensörü kalibre değil: '
                            '/line/calibrate_white ve /line/calibrate_black çağırın')
        self._publish(values, adc_serial.dark_channels(values, self.calibration))

    def _recent_frames(self):
        frames = [v for _, v in self.recent]
        if len(frames) < 10 or time.monotonic() - self.last_frame > SERIAL_TIMEOUT:
            return None
        return frames

    def _srv_white(self, request, response):
        frames = self._recent_frames()
        response.success = frames is not None
        if frames is None:
            response.message = "Deneyap'tan yeterli veri yok"
            return response
        self.white_frames = frames
        median = [int(sorted(c)[len(c) // 2]) for c in zip(*frames)]
        response.message = f'beyaz kaydedildi (mV): {median}; şimdi siyahı ölçün'
        self.get_logger().info(response.message)
        return response

    def _srv_black(self, request, response):
        frames = self._recent_frames()
        response.success = False
        if self.white_frames is None:
            response.message = 'önce /line/calibrate_white'
            return response
        if frames is None:
            response.message = "Deneyap'tan yeterli veri yok"
            return response
        try:
            calibration = adc_serial.make_calibration(self.white_frames, frames)
            adc_serial.save_calibration(self.calibration_path, calibration)
        except (ValueError, OSError) as exc:
            response.message = f'kalibrasyon kaydedilmedi: {exc}'
            self.get_logger().error(response.message)
            return response
        self.calibration = calibration
        self.calibration_stamp = None   # bir sonraki okumada dosya damgası alınır
        self.warned.discard('calibration')
        self.white_frames = None
        response.success = True
        response.message = (f'kalibrasyon kaydedildi: {self.calibration_path} '
                            f'beyaz {[int(v) for v in calibration["white_mv"]]} '
                            f'siyah {[int(v) for v in calibration["black_mv"]]}')
        self.get_logger().info(response.message)
        return response

    # --- GPIO tipleri ---
    def _read(self):
        """Döner: (ham değerler, çizgiyi gören kanallar)."""
        if self.type == 'qtr_rc':
            raw = read_decay_us(self.group, self.count, self.timeout, self.charge)
            dark = dark_channels(raw, self.threshold)
            return raw, [d == self.line_is_dark for d in dark]
        raw = self.group.get_all()
        return raw, [v == self.line_level for v in raw]

    def _tick(self):
        self._publish(*self._read())

    def _publish(self, raw, active):
        reading = read_line(active, self.positions)
        msg = LineState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.sensors = reading.sensors
        msg.raw = [min(int(v), 65535) for v in raw]
        msg.detected = reading.detected
        msg.position = float(reading.position)
        msg.intersection = reading.intersection
        self.pub.publish(msg)

    def destroy_node(self):
        if self.group is not None:
            self.group.release()
        if getattr(self, 'port', None) is not None:
            self.port.close()
        if self.emitter is not None:
            self.emitter.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = LineSensorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
