"""slam_toolbox: haritalama veya kayıtlı harita üzerinde konumlanma.

  slam_mode:=mapping                       yeni harita (varsayılan)
  slam_mode:=localization map:=<yol>       kayıtlı pose graph üzerinde konumlan
                                           (<yol> uzantısız, ör. ~/ika_maps/salon)

Jazzy'de slam_toolbox bir lifecycle node; configure/activate burada yapılır.
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, OpaqueFunction, RegisterEventHandler
from launch.events import matches_action
from launch_ros.actions import LifecycleNode
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from launch_ros.substitutions import FindPackageShare
from lifecycle_msgs.msg import Transition


def _setup(context):
    mode = context.launch_configurations['slam_mode']
    map_path = os.path.expanduser(context.launch_configurations['map'])
    if mode not in ('mapping', 'localization'):
        raise RuntimeError(f"slam_mode mapping veya localization olmalı, gelen: {mode}")

    overrides = {'mode': mode, 'use_sim_time': False}
    if mode == 'localization':
        if not map_path:
            raise RuntimeError('localization için map:=<uzantısız pose graph yolu> verin')
        if not os.path.exists(map_path + '.posegraph'):
            raise RuntimeError(f'{map_path}.posegraph bulunamadı')
        overrides.update({'map_file_name': map_path, 'map_start_at_dock': True})

    share = FindPackageShare('ika_navigation').perform(context)
    params = os.path.join(share, 'config', 'slam.yaml')
    node = LifecycleNode(
        package='slam_toolbox',
        executable='async_slam_toolbox_node' if mode == 'mapping'
        else 'localization_slam_toolbox_node',
        name='slam_toolbox',
        namespace='',
        output='screen',
        parameters=[params, overrides],
    )
    configure = EmitEvent(event=ChangeState(
        lifecycle_node_matcher=matches_action(node),
        transition_id=Transition.TRANSITION_CONFIGURE))
    activate = RegisterEventHandler(OnStateTransition(
        target_lifecycle_node=node, start_state='configuring', goal_state='inactive',
        entities=[EmitEvent(event=ChangeState(
            lifecycle_node_matcher=matches_action(node),
            transition_id=Transition.TRANSITION_ACTIVATE))]))
    return [node, configure, activate]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('slam_mode', default_value='mapping'),
        DeclareLaunchArgument('map', default_value=''),
        OpaqueFunction(function=_setup),
    ])
