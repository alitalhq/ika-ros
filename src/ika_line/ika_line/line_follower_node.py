"""line_follower_node: /line/state -> /cmd_vel/line

Yalnızca mod 'line' iken komut üretir (/ika/mode, mode_manager_node'dan).
Moda her girişte kontrolcü sıfırlanır. Durum /line_follower/status'ta.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from geometry_msgs.msg import Twist
from std_msgs.msg import String

from ika_interfaces.msg import LineState
from ika_line.line_math import LineFollower, LineReading

LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)


class LineFollowerNode(Node):

    def __init__(self):
        super().__init__('line_follower_node')
        defaults = {
            'speed': 0.15, 'kp': 12.0, 'kd': 0.4, 'max_angular': 2.5,
            'min_speed_ratio': 0.3, 'half_width': 0.03, 'search_angular': 1.5,
            'lost_timeout': 1.5, 'intersection_action': 'straight',
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self.follower = LineFollower(**{n: self.get_parameter(n).value for n in defaults})

        self.active = False
        self.last_stamp = None
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel/line', 10)
        self.status_pub = self.create_publisher(String, 'line_follower/status', LATCHED)
        self.create_subscription(String, 'ika/mode', self._on_mode, LATCHED)
        self.create_subscription(LineState, 'line/state', self._on_line, 10)
        self._set_status('idle')

    def _set_status(self, state):
        if getattr(self, '_status', None) != state:
            self._status = state
            self.status_pub.publish(String(data=state))

    def _on_mode(self, msg: String):
        active = msg.data == 'line'
        if active and not self.active:
            self.follower.reset()
            self.last_stamp = None
        self.active = active
        if not active:
            self._set_status('idle')

    def _on_line(self, msg: LineState):
        if not self.active:
            return
        now = self.get_clock().now()
        dt = 0.0 if self.last_stamp is None else (now - self.last_stamp).nanoseconds * 1e-9
        self.last_stamp = now
        reading = LineReading(list(msg.sensors), msg.detected, msg.position, msg.intersection)
        linear, angular = self.follower.update(reading, dt)
        cmd = Twist()
        cmd.linear.x = linear
        cmd.angular.z = angular
        self.cmd_pub.publish(cmd)
        self._set_status(self.follower.state)


def main(args=None):
    rclpy.init(args=args)
    node = LineFollowerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
