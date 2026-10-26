"""RPLIDAR A1'in kendi motor sürücüsünü (CTRL_MOTO hattı) sabit PWM ile besler.

Lidar USB adaptör kartı olmadan doğrudan Gemstone UART'ına bağlandığında
gerekir; USB adaptörle motoru adaptör döndürür.
Eski robotta %100 duty motor gürültüsüyle UART'ı bozup "operation timeout"
hatası verdi; %85 sahada doğrulanan değerdir.
"""

import rclpy
from rclpy.node import Node

from ika_hal.pwm import open_pwm


class LidarMotorNode(Node):

    def __init__(self):
        super().__init__('lidar_motor_node')
        self.declare_parameter('backend', 'gpiod')
        self.declare_parameter('pwm', 'ecap2')
        self.declare_parameter('period_ns', 1_000_000)
        self.declare_parameter('duty_percent', 85.0)

        p = self.get_parameter
        self._pwm = open_pwm(p('pwm').value, p('period_ns').value, p('backend').value)
        if self._pwm is None:
            raise ValueError("lidar_motor_node: 'pwm' boş")
        self._pwm.set_duty_percent(p('duty_percent').value)
        self.get_logger().info(
            f"lidar motoru: {p('pwm').value} duty=%{p('duty_percent').value:.0f}")

    def destroy_node(self):
        self._pwm.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = LidarMotorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
