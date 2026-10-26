"""line_sensor_node: çizgi sensörü dizisini GPIO'dan okur.

type: qtr_rc   Pololu QTR-8RC / QTR-xRC (RC tipi, kanal başına 1 GPIO).
               `qtr.threshold_us` üstündeki boşalma süresi = koyu zemin.
type: digital  TCRT5000 vb. modüllerin dijital (DO) çıkışı;
               `line_level` = sensör çizgiyi görünce okunan seviye.

`pins` soldan sağa sıralanır (robotun arkasından, ileri bakarak). 3.3 V lojik!
Yayın: /line/state (ika_interfaces/LineState)
"""

import rclpy
from rclpy.node import Node

from ika_hal.gpio import open_chip, resolve_pin
from ika_interfaces.msg import LineState
from ika_line.line_math import read_line, sensor_positions
from ika_line.qtr import dark_channels, read_decay_us


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

        p = lambda name: self.get_parameter(name).value  # noqa: E731
        backend = p('backend')
        self.type = p('type')
        if self.type not in ('qtr_rc', 'digital'):
            raise ValueError(f"type qtr_rc veya digital olmalı, gelen: {self.type!r}")
        pins = [resolve_pin(s, backend) for s in p('pins') if s.strip()]
        if not pins and backend == 'mock':
            pins = [resolve_pin(f'GPIO{100 + i}', 'mock') for i in range(8)]
        if not pins:
            raise ValueError("line_sensor_node: 'pins' boş (ör. ['GPIO6', 'GPIO19', ...])")

        self.count = len(pins)
        self.positions = sensor_positions(self.count, p('spacing'))
        self.frame_id = p('frame_id')
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

        self.pub = self.create_publisher(LineState, 'line/state', 10)
        self.create_timer(1.0 / p('rate'), self._tick)
        self.get_logger().info(
            f'{self.type}: {self.count} kanal, aralık {p("spacing") * 1000:.1f} mm'
            + (f', eşik {self.threshold} µs' if self.type == 'qtr_rc' else ''))

    def _read(self):
        """Döner: (ham değerler, çizgiyi gören kanallar)."""
        if self.type == 'qtr_rc':
            raw = read_decay_us(self.group, self.count, self.timeout, self.charge)
            dark = dark_channels(raw, self.threshold)
            return raw, [d == self.line_is_dark for d in dark]
        raw = self.group.get_all()
        return raw, [v == self.line_level for v in raw]

    def _tick(self):
        raw, active = self._read()
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
        self.group.release()
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
