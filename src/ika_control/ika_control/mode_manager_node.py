"""mode_manager_node: robotun tek /cmd_vel kaynağı.

Girdiler   : /cmd_vel/teleop, /cmd_vel/line, /cmd_vel/nav, /scan, /goal_pose
Çıktılar   : /cmd_vel, /ika/mode (latched String), /ika/estop_active (latched Bool),
             /ika/obstacle_distance (Float32, hareket yönündeki koridorda en yakın
             engelin gövdeye uzaklığı)
Servisler  : /ika/set_mode (ika_interfaces/SetMode), /ika/estop (std_srvs/SetBool)

/goal_pose'a (GCS veya RViz) hedef gelince otomatik 'nav' moduna geçilir.
nav modundan çıkarken veya acil durdurmada Nav2 hedefleri iptal edilir.
"""

import math
import time

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rclpy.time import Time
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import PoseStamped, Twist
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, Float32, String
from std_srvs.srv import SetBool
from tf2_ros import Buffer, TransformException, TransformListener

from ika_control.mux import CommandMux
from ika_control.safety import corridor_gap, Footprint, LidarPose, limit_linear
from ika_interfaces.srv import SetMode

LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)


class ModeManagerNode(Node):

    def __init__(self):
        super().__init__('mode_manager_node')
        self.declare_parameter('rate', 20.0)
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('teleop_takeover', True)
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('safety.enabled', True)
        self.declare_parameter('safety.stop_distance', 0.10)
        self.declare_parameter('safety.slow_distance', 0.35)
        self.declare_parameter('safety.side_margin', 0.01)
        self.declare_parameter('safety.scan_timeout', 0.5)
        # Gövde sınırları; robot.launch.py robot.yaml'dan doldurur.
        self.declare_parameter('footprint.front', 0.17)
        self.declare_parameter('footprint.rear', 0.09)
        self.declare_parameter('footprint.half_width', 0.09)
        p = lambda name: self.get_parameter(name).value  # noqa: E731

        self.mux = CommandMux(p('cmd_timeout'), p('teleop_takeover'))
        self.base_frame = p('base_frame')
        self.safety = p('safety.enabled')
        self.stop_distance = p('safety.stop_distance')
        self.slow_distance = p('safety.slow_distance')
        self.side_margin = p('safety.side_margin')
        self.scan_timeout = p('safety.scan_timeout')
        self.body = Footprint(p('footprint.front'), p('footprint.rear'),
                              p('footprint.half_width'))
        self.scan = None
        self.scan_time = 0.0
        self.lidar = None

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.mode_pub = self.create_publisher(String, 'ika/mode', LATCHED)
        self.estop_pub = self.create_publisher(Bool, 'ika/estop_active', LATCHED)
        self.obstacle_pub = self.create_publisher(Float32, 'ika/obstacle_distance', 10)

        for source in ('teleop', 'line', 'nav'):
            self.create_subscription(
                Twist, f'cmd_vel/{source}',
                lambda msg, s=source: self._on_cmd(s, msg), 10)
        self.create_subscription(LaserScan, 'scan', self._on_scan, qos_profile_sensor_data)
        self.create_subscription(PoseStamped, 'goal_pose', self._on_goal, 10)

        self.create_service(SetMode, 'ika/set_mode', self._srv_set_mode)
        self.create_service(SetBool, 'ika/estop', self._srv_estop)
        self.cancel_client = self.create_client(CancelGoal, 'navigate_to_pose/_action/cancel_goal')

        self._publish_state()
        self.create_timer(1.0 / p('rate'), self._tick)
        self.get_logger().info('mod: idle (host /ika/set_mode ile değiştirir)')

    # --- durum ---
    def _change_mode(self, mode: str):
        previous = self.mux.mode
        ok, message = self.mux.set_mode(mode)
        if ok:
            self._after_mode_change(previous)
        return ok, message

    def _after_mode_change(self, previous: str):
        if previous == 'nav' and self.mux.mode != 'nav':
            self._cancel_nav()
        self._publish_state()
        self.get_logger().info(f'mod: {previous} -> {self.mux.mode}')

    def _publish_state(self):
        self.mode_pub.publish(String(data=self.mux.mode))
        self.estop_pub.publish(Bool(data=self.mux.estop))

    def _cancel_nav(self):
        if self.cancel_client.service_is_ready():
            # Boş goal_info = tüm hedefleri iptal et.
            self.cancel_client.call_async(CancelGoal.Request())

    # --- girdiler ---
    def _on_cmd(self, source: str, msg: Twist):
        previous = self.mux.mode
        if self.mux.feed(source, msg.linear.x, msg.angular.z, time.monotonic()):
            self.get_logger().warn(f'teleop devraldı ({previous} modundan)')
            self._after_mode_change(previous)

    def _on_scan(self, msg: LaserScan):
        self.scan = msg
        self.scan_time = time.monotonic()
        if self.lidar is None:
            try:
                tf = self.tf_buffer.lookup_transform(
                    self.base_frame, msg.header.frame_id, Time(), Duration(seconds=0.0))
            except TransformException:
                return
            t, q = tf.transform.translation, tf.transform.rotation
            self.lidar = LidarPose(t.x, t.y, math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                                                        1.0 - 2.0 * (q.y * q.y + q.z * q.z)))

    def _on_goal(self, msg: PoseStamped):
        if self.mux.estop:
            self.get_logger().warn('acil durdurma aktif: nav hedefi iptal edildi')
            self._cancel_nav()
            return
        if self.mux.mode != 'nav':
            self._change_mode('nav')

    # --- servisler ---
    def _srv_set_mode(self, request, response):
        response.success, response.message = self._change_mode(request.mode.strip().lower())
        return response

    def _srv_estop(self, request, response):
        previous = self.mux.mode
        self.mux.set_estop(request.data)
        if request.data:
            self.cmd_pub.publish(Twist())
            self.get_logger().error('ACİL DURDURMA')
        else:
            self.get_logger().info('acil durdurma kaldırıldı (mod: idle)')
        self._after_mode_change(previous)
        response.success = True
        response.message = 'aktif' if request.data else 'kaldırıldı'
        return response

    # --- döngü ---
    def _tick(self):
        linear, angular = self.mux.output(time.monotonic())
        if self.safety and linear != 0.0:
            distance = self._obstacle_distance(forward=linear > 0.0)
            if distance is not None:
                linear = math.copysign(
                    limit_linear(abs(linear), distance, self.stop_distance, self.slow_distance),
                    linear)
                self.obstacle_pub.publish(Float32(data=float(min(distance, 99.0))))
        cmd = Twist()
        cmd.linear.x = linear
        cmd.angular.z = angular
        self.cmd_pub.publish(cmd)

    def _obstacle_distance(self, forward: bool):
        if self.scan is None or time.monotonic() - self.scan_time > self.scan_timeout:
            return None   # lidar yoksa fren devre dışı (ör. mock)
        s = self.scan
        return corridor_gap(s.ranges, s.angle_min, s.angle_increment,
                            self.lidar or LidarPose(), self.body, forward,
                            self.side_margin, s.range_min, s.range_max)


def main(args=None):
    rclpy.init(args=args)
    node = ModeManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
