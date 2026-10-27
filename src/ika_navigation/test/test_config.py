import os

import yaml

CONFIG = os.path.join(os.path.dirname(__file__), '..', 'config')


def _load(name):
    with open(os.path.join(CONFIG, name)) as f:
        return yaml.safe_load(f)


def _values(tree, key):
    """İç içe yaml'daki tüm `key` değerleri."""
    if isinstance(tree, dict):
        for k, v in tree.items():
            if k == key:
                yield v
            yield from _values(v, key)


def test_slam_frames_match_tf_tree():
    slam = _load('slam.yaml')
    assert set(_values(slam, 'map_frame')) == {'map'}
    assert set(_values(slam, 'odom_frame')) == {'odom'}
    assert set(_values(slam, 'base_frame')) == {'base_footprint'}


def test_nav2_uses_fused_odometry_and_base_link():
    nav = _load('nav2.yaml')
    assert set(_values(nav, 'odom_topic')) == {'/odometry/filtered'}
    assert set(_values(nav, 'robot_base_frame')) == {'base_link'}


def test_costmaps_share_robot_radius():
    # Ölçüler değişince iki costmap birlikte güncellenmeli.
    radii = set(_values(_load('nav2.yaml'), 'robot_radius'))
    assert len(radii) == 1
    assert 0.05 < radii.pop() < 1.0
