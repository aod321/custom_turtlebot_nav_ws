"""Continuously broadcast rplidar_link and camera_link TF on /tf (dynamic).

Workaround for SLAM/AMCL not receiving /tf_static from RSP due to DDS issues.
Publishing on /tf as dynamic transforms ensures late-joining subscribers receive them.
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
import math


class TfBroadcasterNode(Node):

    def __init__(self):
        super().__init__('tf_broadcaster')
        self.br = TransformBroadcaster(self)
        # Publish at 10Hz (lower rate to avoid timestamp issues with scan messages)
        self.timer = self.create_timer(0.1, self.broadcast)
        self.get_logger().info('TF broadcaster started (rplidar_link + camera_link)')

    def broadcast(self):
        now = self.get_clock().now().to_msg()

        # rplidar_link: 3cm behind, 12cm high, yaw=90° (triangle points left)
        t1 = TransformStamped()
        t1.header.stamp = now
        t1.header.frame_id = 'base_link'
        t1.child_frame_id = 'rplidar_link'
        t1.transform.translation.x = -0.03
        t1.transform.translation.y = 0.0
        t1.transform.translation.z = 0.12
        # yaw = -pi/2 = -90 degrees
        t1.transform.rotation.w = math.cos(-1.5708 / 2)
        t1.transform.rotation.z = math.sin(-1.5708 / 2)

        # camera_link: 15cm behind, 42cm high, facing forward
        t2 = TransformStamped()
        t2.header.stamp = now
        t2.header.frame_id = 'base_link'
        t2.child_frame_id = 'camera_link'
        t2.transform.translation.x = -0.15
        t2.transform.translation.y = 0.0
        t2.transform.translation.z = 0.42
        t2.transform.rotation.w = 1.0

        self.br.sendTransform([t1, t2])


def main(args=None):
    rclpy.init(args=args)
    node = TfBroadcasterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
