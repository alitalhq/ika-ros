"""RPLIDAR sürücüsünü (sllidar_node) seçilen bağlantıyla çalıştırır.

  usb   lidarın USB adaptörü; port /dev/serial/by-id altında kendiliğinden bulunur
  gpio  adaptörsüz: Gemstone UART'ı (/dev/ttyS3) + lidar motoru için PWM (ecap2)

Bağlantı /ika/set_lidar servisiyle (arayüzdeki Lidar paneli) değiştirilir ve
`state_file`'a kaydedilir; robot yeniden açılınca aynı bağlantı kullanılır.
Sürücü kapanırsa (ör. USB kablosu çıktı) `restart_delay` sonra yeniden başlatılır.
Durum /ika/lidar'da yayınlanır.

Eski robotta GPIO bağlantısında %100 duty motor gürültüsüyle UART'ı bozup
"operation timeout" hatası verdi; %85 sahada doğrulanan değerdir.
"""

import ctypes
import os
import signal
import subprocess
import time

from ament_index_python.packages import get_package_prefix, PackageNotFoundError
from ika_interfaces.msg import LidarStatus
from ika_interfaces.srv import SetLidar
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

from ika_hal.lidar import (choose_source, find_usb_port, load_choice, RateMeter, save_choice,
                           sllidar_arguments, SOURCES)
from ika_hal.pwm import open_pwm

LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
PR_SET_PDEATHSIG = 1


def _die_with_parent():
    # Yönetici beklenmedik şekilde ölürse sürücü sahipsiz kalıp portu tutmasın.
    try:
        ctypes.CDLL('libc.so.6', use_errno=True).prctl(PR_SET_PDEATHSIG, signal.SIGTERM)
    except (OSError, AttributeError):
        pass


class LidarManagerNode(Node):

    def __init__(self):
        super().__init__('lidar_manager_node')
        for name, default in {
            'backend': 'gpiod',
            'source': 'usb',
            'source_override': '',
            'port_override': '',
            'state_file': '~/.ika/lidar_source',
            'baudrate': 115200,
            'frame_id': 'lidar_link',
            'inverted': False,
            'angle_compensate': True,
            'restart_delay': 3.0,
            'usb.port': '',
            'gpio.port': '/dev/ttyS3',
            'gpio.pwm': 'ecap2',
            'gpio.period_ns': 1_000_000,
            'gpio.duty_percent': 85.0,
        }.items():
            self.declare_parameter(name, default)
        p = lambda name: self.get_parameter(name).value  # noqa: E731
        self._p = p
        self._state_file = os.path.expanduser(p('state_file'))

        try:
            prefix = get_package_prefix('sllidar_ros2')
            self._driver = os.path.join(prefix, 'lib', 'sllidar_ros2', 'sllidar_node')
        except PackageNotFoundError:
            self._driver = ''

        self._proc = None
        self._pwm = None
        self._port = ''
        self._message = ''
        self._retry_at = 0.0
        self._rate = RateMeter()

        self._status_pub = self.create_publisher(LidarStatus, 'ika/lidar', LATCHED)
        self.create_subscription(LaserScan, 'scan', self._on_scan, qos_profile_sensor_data)
        self.create_service(SetLidar, 'ika/set_lidar', self._on_set)
        self.create_timer(1.0, self._watch)

        self._source = choose_source(p('source_override'), load_choice(self._state_file),
                                     p('source'))
        self.get_logger().info(f'lidar bağlantısı: {self._source}')
        self._start()

    # --- sürücü ----------------------------------------------------------------
    def _resolve_port(self) -> str:
        if self._p('port_override'):
            return self._p('port_override')
        if self._source == 'usb':
            return self._p('usb.port') or find_usb_port()
        return self._p('gpio.port')

    def _set_motor(self, on: bool):
        if on and self._pwm is None:
            self._pwm = open_pwm(self._p('gpio.pwm'), self._p('gpio.period_ns'),
                                 self._p('backend'))
            if self._pwm is not None:
                self._pwm.set_duty_percent(self._p('gpio.duty_percent'))
        elif not on and self._pwm is not None:
            self._pwm.release()
            self._pwm = None

    def _start(self):
        self._retry_at = 0.0
        try:
            self._set_motor(self._source == 'gpio')
        except (OSError, ValueError) as e:
            return self._fail(f"lidar motor PWM'i açılamadı ({self._p('gpio.pwm')}): {e}")

        self._port = self._resolve_port()
        if not self._driver:
            return self._fail('sllidar_ros2 paketi kurulu değil')
        if not self._port or not os.path.exists(self._port):
            hint = ('USB adaptörü takılı mı?' if self._source == 'usb'
                    else "UART overlay'i ve pin 8/10 bağlantısı?")
            return self._fail(f"lidar portu yok: {self._port or '(bulunamadı)'}; {hint}")

        args = sllidar_arguments(self._port, self._p('baudrate'), self._p('frame_id'),
                                 self._p('inverted'), self._p('angle_compensate'))
        try:
            self._proc = subprocess.Popen([self._driver, *args], preexec_fn=_die_with_parent)
        except OSError as e:
            return self._fail(f'sllidar_node başlatılamadı: {e}')
        self._message = f'{self._source}: {self._port}'
        self.get_logger().info(f'sllidar_node başlatıldı ({self._message})')
        self._publish()

    def _fail(self, message: str):
        if message != self._message:
            self.get_logger().warn(message)
        self._message = message
        self._retry_at = time.monotonic() + self._p('restart_delay')
        self._publish()

    def _stop(self):
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    def _watch(self):
        if self._proc is not None and self._proc.poll() is not None:
            code = self._proc.returncode
            self._proc = None
            self._fail(f'sllidar_node kapandı (kod {code}); yeniden başlatılacak')
        elif self._proc is None and self._retry_at and time.monotonic() >= self._retry_at:
            self._start()
        self._publish()

    # --- ROS arayüzü ---------------------------------------------------------
    def _on_scan(self, _msg):
        self._rate.tick(time.monotonic())

    def _on_set(self, request, response):
        source = request.source.strip().lower()
        if source not in SOURCES:
            response.success = False
            response.message = f"bilinmeyen bağlantı '{request.source}' (usb | gpio)"
            return response
        try:
            save_choice(self._state_file, source)
            saved = ''
        except OSError as e:
            saved = f' (kaydedilemedi: {e})'
        if source == self._source and self._proc is not None:
            response.success = True
            response.message = f'lidar zaten {source}{saved}'
            return response

        self.get_logger().info(f'lidar bağlantısı değişiyor: {self._source} -> {source}')
        self._stop()
        self._source = source
        self._rate = RateMeter()
        self._start()
        response.success = self._proc is not None
        response.message = (f'lidar: {self._message}' if response.success
                            else f'lidar {source} seçildi ama başlamadı: {self._message}') + saved
        return response

    def _publish(self):
        self._status_pub.publish(LidarStatus(
            source=self._source, port=self._port, running=self._proc is not None,
            rate_hz=float(self._rate.rate(time.monotonic())), message=self._message))

    def destroy_node(self):
        self._stop()
        self._set_motor(False)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = LidarManagerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
