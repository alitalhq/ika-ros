"""robot_state_publisher: URDF'i yayınlar ve sabit sensör TF'lerini üretir.

Teker eklemlerinin açıları ika_base_node'un /joint_states topic'inden gelir.
"""

from launch import LaunchDescription
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    xacro_file = PathJoinSubstitution(
        [FindPackageShare('ika_description'), 'urdf', 'ika.urdf.xacro'])

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': ParameterValue(
                    Command(['xacro ', xacro_file]), value_type=str),
            }],
        ),
    ])
