"""ROS + pseudo-terminal test. No GPIO, motors or real serial device are used."""

import json
import os
import time

import pytest

rclpy = pytest.importorskip('rclpy')
if os.name != 'posix':
    pytest.skip('pseudo-terminal requires POSIX', allow_module_level=True)

from geometry_msgs.msg import Twist  # noqa: E402
from rclpy.executors import SingleThreadedExecutor  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import DurabilityPolicy, QoSProfile  # noqa: E402
from std_msgs.msg import String  # noqa: E402
from std_srvs.srv import Trigger  # noqa: E402

from ika_line.line_sensor_node import LineSensorNode  # noqa: E402


def test_calibration_services_with_live_serial_frames(tmp_path):
    master, slave = os.openpty()
    path = tmp_path / 'calibration.json'
    old = {'white_mv': [500] * 8, 'black_mv': [3000] * 8}
    path.write_text(json.dumps(old))
    # A namespace isolates services/topics even when colcon tests share a domain.
    rclpy.init(args=['--ros-args', '-r', '__ns:=/calibration_test',
                     '-p', 'type:=serial', '-p', f'serial.port:={os.ttyname(slave)}',
                     '-p', f'serial.calibration:={path}'])
    sensor = LineSensorNode()
    driver = Node('calibration_test_driver')
    executor = SingleThreadedExecutor()
    executor.add_node(sensor)
    executor.add_node(driver)
    latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    mode_pub = driver.create_publisher(String, 'ika/mode', latched)
    cmd_pub = driver.create_publisher(Twist, 'cmd_vel', 10)
    white = driver.create_client(Trigger, 'line/calibrate_white')
    black = driver.create_client(Trigger, 'line/calibrate_black')
    seq = 0

    def pump(value, duration=1.4):
        nonlocal seq
        until = time.monotonic() + duration
        while time.monotonic() < until:
            seq += 1
            os.write(master, (json.dumps({'ika_adc': 1, 'seq': seq,
                                         'mv': [value] * 8}) + '\n').encode())
            cmd_pub.publish(Twist())
            executor.spin_once(timeout_sec=0.01)
            time.sleep(0.01)

    def invoke(client):
        assert client.wait_for_service(timeout_sec=3)
        future = client.call_async(Trigger.Request())
        executor.spin_until_future_complete(future, timeout_sec=3)
        assert future.done()
        return future.result()

    try:
        mode_pub.publish(String(data='manual'))
        pump(1000)
        assert not invoke(white).success
        mode_pub.publish(String(data='idle'))
        pump(1000)
        assert not invoke(black).success
        assert invoke(white).success
        assert json.loads(path.read_text()) == old
        pump(1050)
        assert not invoke(black).success
        assert json.loads(path.read_text()) == old
        pump(2800)
        assert invoke(black).success
        assert json.loads(path.read_text()) == {'white_mv': [1000] * 8,
                                                'black_mv': [2800] * 8}
        assert sensor.calibration['black_mv'] == [2800] * 8
        pump(1000)
        assert invoke(white).success
        # A lost sensor must not allow reusing its last valid surface window.
        until = time.monotonic() + 0.7
        while time.monotonic() < until:
            cmd_pub.publish(Twist())
            executor.spin_once(timeout_sec=0.02)
        assert not invoke(black).success
        assert sensor.session.white is None
    finally:
        executor.shutdown()
        sensor.destroy_node()
        driver.destroy_node()
        rclpy.shutdown()
        os.close(master)
        os.close(slave)
