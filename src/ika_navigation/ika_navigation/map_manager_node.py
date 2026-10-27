"""map_manager_node: /ika/save_map ile SLAM haritasını robot üzerine kaydeder.

Tek çağrıda iki dosya grubu yazılır (map_dir altında, uzantısız `name`):
  name.pgm / name.yaml        -> görüntü harita (Nav2 map_server, paylaşım)
  name.posegraph / name.data  -> slam_toolbox pose graph; sonra
                                 `slam_mode:=localization map:=<yol>` ile açılır
"""

from datetime import datetime
import os
import re
import threading

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from slam_toolbox.srv import SaveMap, SerializePoseGraph
from std_msgs.msg import String

from ika_interfaces.srv import SaveMap as IkaSaveMap

_NAME = re.compile(r'^[A-Za-z0-9_\-]{1,64}$')


class MapManagerNode(Node):

    def __init__(self):
        super().__init__('map_manager_node')
        self.declare_parameter('map_dir', '~/ika_maps')
        self.declare_parameter('timeout', 10.0)
        self.map_dir = os.path.expanduser(self.get_parameter('map_dir').value)
        self.timeout = self.get_parameter('timeout').value
        os.makedirs(self.map_dir, exist_ok=True)

        group = ReentrantCallbackGroup()
        self.save_client = self.create_client(
            SaveMap, 'slam_toolbox/save_map', callback_group=group)
        self.serialize_client = self.create_client(
            SerializePoseGraph, 'slam_toolbox/serialize_map', callback_group=group)
        self.create_service(IkaSaveMap, 'ika/save_map', self._on_save, callback_group=group)
        self.get_logger().info(f'haritalar: {self.map_dir}')

    def _call(self, client, request):
        if not client.wait_for_service(timeout_sec=2.0):
            return None
        # Reentrant grup + çok iş parçacıklı executor: yanıtı başka bir
        # thread işler, burada beklemek kilitlenmez.
        done = threading.Event()
        future = client.call_async(request)
        future.add_done_callback(lambda _: done.set())
        if not done.wait(self.timeout):
            return None
        return future.result()

    def _on_save(self, request, response):
        name = request.name.strip() or datetime.now().strftime('harita_%Y%m%d_%H%M%S')
        if not _NAME.match(name):
            response.success = False
            response.message = 'isim yalnızca harf, rakam, _ ve - içerebilir'
            return response
        path = os.path.join(self.map_dir, name)

        image = self._call(self.save_client, SaveMap.Request(name=String(data=path)))
        graph = self._call(self.serialize_client, SerializePoseGraph.Request(filename=path))
        problems = []
        if image is None or image.result != 0:
            problems.append('görüntü harita')
        if graph is None or graph.result != 0:
            problems.append('pose graph')

        response.path = path
        response.success = not problems
        response.message = (f'kaydedildi: {path}' if not problems else
                            'kaydedilemedi: ' + ', '.join(problems) +
                            ' (slam_toolbox çalışıyor mu?)')
        log = self.get_logger().info if response.success else self.get_logger().error
        log(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = MapManagerNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
