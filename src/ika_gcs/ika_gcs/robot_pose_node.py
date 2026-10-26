"""robot_pose_node: tarayıcı TF okuyamadığı için robot konumunu yayınlar.

/ika/robot_pose (PoseStamped): map -> base_link varsa map çerçevesinde
(SLAM açık), yoksa odom çerçevesinde.
"""

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from geometry_msgs.msg import PoseStamped
from tf2_ros import Buffer, TransformException, TransformListener


class RobotPoseNode(Node):

    def __init__(self):
        super().__init__('robot_pose_node')
        self.declare_parameter('frames', ['map', 'odom'])
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('rate', 10.0)
        self.frames = list(self.get_parameter('frames').value)
        self.base_frame = self.get_parameter('base_frame').value
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.pub = self.create_publisher(PoseStamped, 'ika/robot_pose', 10)
        self.create_timer(1.0 / self.get_parameter('rate').value, self._tick)

    def _tick(self):
        for frame in self.frames:
            try:
                tf = self.buffer.lookup_transform(frame, self.base_frame, Time())
            except TransformException:
                continue
            msg = PoseStamped()
            msg.header = tf.header
            msg.pose.position.x = tf.transform.translation.x
            msg.pose.position.y = tf.transform.translation.y
            msg.pose.orientation = tf.transform.rotation
            self.pub.publish(msg)
            return


def main(args=None):
    rclpy.init(args=args)
    node = RobotPoseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
