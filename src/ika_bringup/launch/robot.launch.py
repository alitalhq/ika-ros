"""İKA robotunu tek komutla başlatır.

  ros2 launch ika_bringup robot.launch.py                    # tam robot, haritalama
  ros2 launch ika_bringup robot.launch.py nav:=true          # + Nav2 hedefe gitme
  ros2 launch ika_bringup robot.launch.py slam_mode:=localization map:=~/ika_maps/salon nav:=true
  ros2 launch ika_bringup robot.launch.py backend:=mock      # donanımsız (laptop)

Argümanlar:
  backend      gpiod | mock     mock: motor/enkoder benzetimi, IMU ve lidar kapalı
  hardware     <yaml>           pin/donanım dosyası (varsayılan config/hardware.yaml)
  imu          true | false     ICM-20948
  fusion       true | false     EKF (teker + IMU) odom TF'ini yayınlar;
                                false ise ika_base_node yayınlar
  lidar        true | false     RPLIDAR A1 (sllidar_ros2, lidar_manager_node üzerinden)
  lidar_source <boş> | usb | gpio  boşsa arayüzde seçilip kaydedilen, o da yoksa
                                hardware.yaml'daki (usb) bağlantı
  lidar_port   <boş>            seri portu elle ver (ör. /dev/ttyUSB1)
  line         true | false     çizgi sensörü + çizgi izleme (hardware.yaml'da type: serial
                                ise Deneyap UART'ı GPIO lidara kapatılır)
  slam         true | false     slam_toolbox + harita kaydetme servisi
  slam_mode    mapping | localization
  map          <yol>            localization için uzantısız pose graph yolu
  nav          true | false     Nav2
  gcs          true | false     rosbridge + web arayüzü (http://<robot>:8000)
"""

import os

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

ARGS = {
    'backend': 'gpiod',
    'hardware': '',
    'imu': 'true',
    'fusion': 'true',
    'lidar': 'true',
    'lidar_source': '',
    'lidar_port': '',
    'line': 'true',
    'slam': 'true',
    'slam_mode': 'mapping',
    'map': '',
    'nav': 'false',
    'gcs': 'true',
}


def _share(package, context):
    return FindPackageShare(package).perform(context)


def _include(package, launch_file, context, **arguments):
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(_share(package, context), 'launch', launch_file)),
        launch_arguments=arguments.items())


def _setup(context):
    arg = context.launch_configurations
    flag = lambda name: arg[name].lower() in ('true', '1', 'yes')  # noqa: E731
    backend = arg['backend']
    mock = backend == 'mock'
    bringup = _share('ika_bringup', context)
    hardware = (os.path.expanduser(arg['hardware'])
                or os.path.join(bringup, 'config', 'hardware.yaml'))
    control = os.path.join(bringup, 'config', 'control.yaml')
    with open(os.path.join(_share('ika_description', context), 'config', 'robot.yaml')) as f:
        geometry = yaml.safe_load(f)

    with open(hardware) as f:
        line_params = (yaml.safe_load(f) or {}).get('line_sensor_node', {}).get(
            'ros__parameters', {})
    # Deneyap çizgi sensörü UART'ı kullanıyorsa GPIO lidar aynı portu açmasın.
    line_port = (line_params.get('serial', {}).get('port', '/dev/ttyS3')
                 if flag('line') and line_params.get('type') == 'serial' else '')

    fusion = flag('fusion')
    odom_topic = '/odometry/filtered' if fusion else '/wheel/odom'
    actions = [_include('ika_description', 'description.launch.py', context)]

    actions.append(Node(
        package='ika_base', executable='ika_base_node', output='screen',
        parameters=[hardware, {
            'backend': backend,
            'wheel_radius': float(geometry['wheel_radius']),
            'wheel_separation': float(geometry['wheel_separation']),
            'publish_tf': not fusion,
        }]))

    if flag('imu') and not mock:
        actions.append(Node(package='ika_imu', executable='ika_imu_node', output='screen',
                            parameters=[hardware]))
    if fusion:
        actions.append(Node(
            package='robot_localization', executable='ekf_node', name='ekf_filter_node',
            output='screen', parameters=[os.path.join(bringup, 'config', 'ekf.yaml')]))

    if flag('lidar') and not mock:
        actions.append(Node(
            package='ika_hal', executable='lidar_manager_node', output='screen',
            parameters=[hardware, {
                'backend': backend,
                'source_override': arg['lidar_source'],
                'port_override': arg['lidar_port'],
                'busy_port': line_port,
            }]))

    if flag('line'):
        actions.append(Node(package='ika_line', executable='line_sensor_node', output='screen',
                            parameters=[hardware, {'backend': backend}]))
        actions.append(Node(package='ika_line', executable='line_follower_node', output='screen',
                            parameters=[control]))

    chassis = geometry['chassis']
    actions.append(Node(
        package='ika_control', executable='mode_manager_node', output='screen',
        parameters=[control, {
            'footprint.front': float(chassis['x'] + chassis['length'] / 2),
            'footprint.rear': float(chassis['length'] / 2 - chassis['x']),
            'footprint.half_width': float(chassis['width'] / 2),
            'lidar.x': float(geometry['lidar']['x']),
            'lidar.y': float(geometry['lidar']['y']),
            'lidar.yaw': float(geometry['lidar']['yaw']),
        }]))

    if flag('slam'):
        actions.append(_include('ika_navigation', 'slam.launch.py', context,
                                slam_mode=arg['slam_mode'], map=arg['map']))
        actions.append(Node(package='ika_navigation', executable='map_manager_node',
                            output='screen',
                            parameters=[control, {'slam_mode': arg['slam_mode']}]))
    if flag('nav'):
        actions.append(_include('ika_navigation', 'nav.launch.py', context, odom_topic=odom_topic))
    if flag('gcs'):
        actions.append(_include('ika_gcs', 'gcs.launch.py', context))
    return actions


def generate_launch_description():
    return LaunchDescription(
        [DeclareLaunchArgument(name, default_value=value) for name, value in ARGS.items()]
        + [OpaqueFunction(function=_setup)])
