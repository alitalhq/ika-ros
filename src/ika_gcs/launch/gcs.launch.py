"""Host kontrol arayüzü (robot üzerinde çalışır).

  rosbridge_websocket  ws://<robot>:9090   tarayıcı <-> ROS köprüsü
  http.server          http://<robot>:8000 web arayüzü (share/ika_gcs/web)
  robot_pose_node      /ika/robot_pose     harita üzerinde robot konumu

Host'ta yalnızca tarayıcı gerekir: http://<robot-ip>:8000
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    web_root = PathJoinSubstitution([FindPackageShare('ika_gcs'), 'web'])
    return LaunchDescription([
        DeclareLaunchArgument('rosbridge_port', default_value='9090'),
        DeclareLaunchArgument('web_port', default_value='8000'),
        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            output='screen',
            parameters=[{
                'port': ParameterValue(LaunchConfiguration('rosbridge_port'), value_type=int),
                'address': '0.0.0.0',
            }],
        ),
        Node(package='ika_gcs', executable='robot_pose_node', output='screen'),
        ExecuteProcess(
            cmd=['python3', '-m', 'http.server', LaunchConfiguration('web_port'),
                 '--bind', '0.0.0.0', '--directory', web_root],
            output='log',
        ),
    ])
