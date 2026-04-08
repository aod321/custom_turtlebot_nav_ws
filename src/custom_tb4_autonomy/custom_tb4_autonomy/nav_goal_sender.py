"""Utility for sending navigation goals to Nav2."""
import math


def euler_to_quaternion(yaw, pitch=0.0, roll=0.0):
    """Convert Euler angles (radians) to quaternion (w, x, y, z)."""
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return (w, x, y, z)


def make_pose_stamped(x, y, theta, frame_id='map', stamp=None):
    """Create a PoseStamped dict (usable without ROS2 for testing)."""
    w, qx, qy, qz = euler_to_quaternion(theta)
    return {
        'frame_id': frame_id,
        'stamp': stamp,
        'position': {'x': float(x), 'y': float(y), 'z': 0.0},
        'orientation': {'w': w, 'x': qx, 'y': qy, 'z': qz},
    }


# --- ROS2 Node ---

def make_nav_goal_sender_class():
    import rclpy
    from rclpy.node import Node
    from rclpy.action import ActionClient
    from nav2_msgs.action import NavigateToPose
    from geometry_msgs.msg import PoseStamped

    class NavGoalSender(Node):

        def __init__(self):
            super().__init__('nav_goal_sender')
            self._client = ActionClient(
                self, NavigateToPose, '/navigate_to_pose')
            self._current_goal_handle = None

        def wait_for_server(self, timeout_sec=10.0):
            return self._client.wait_for_server(timeout_sec=timeout_sec)

        def send_goal(self, x, y, theta, frame_id='map'):
            """Send a navigation goal. Returns the goal handle future."""
            goal = NavigateToPose.Goal()
            goal.pose = PoseStamped()
            goal.pose.header.frame_id = frame_id
            goal.pose.header.stamp = self.get_clock().now().to_msg()
            goal.pose.pose.position.x = float(x)
            goal.pose.pose.position.y = float(y)
            goal.pose.pose.position.z = 0.0
            w, qx, qy, qz = euler_to_quaternion(theta)
            goal.pose.pose.orientation.w = w
            goal.pose.pose.orientation.x = qx
            goal.pose.pose.orientation.y = qy
            goal.pose.pose.orientation.z = qz

            self.get_logger().info(
                'Sending goal: ({:.2f}, {:.2f}, {:.2f})'.format(x, y, theta))

            send_future = self._client.send_goal_async(
                goal, feedback_callback=self._feedback_cb)
            send_future.add_done_callback(self._goal_response_cb)
            return send_future

        def cancel_goal(self):
            if self._current_goal_handle is not None:
                self.get_logger().info('Cancelling current goal')
                return self._current_goal_handle.cancel_goal_async()
            return None

        def _goal_response_cb(self, future):
            goal_handle = future.result()
            if not goal_handle.accepted:
                self.get_logger().warn('Goal rejected')
                return
            self.get_logger().info('Goal accepted')
            self._current_goal_handle = goal_handle
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(self._result_cb)

        def _result_cb(self, future):
            result = future.result()
            self.get_logger().info(
                'Navigation result: {}'.format(result.status))
            self._current_goal_handle = None

        def _feedback_cb(self, feedback_msg):
            pos = feedback_msg.feedback.current_pose.pose.position
            self.get_logger().debug(
                'Position: ({:.2f}, {:.2f})'.format(pos.x, pos.y))

    return NavGoalSender


def main(args=None):
    import rclpy
    rclpy.init(args=args)
    cls = make_nav_goal_sender_class()
    node = cls()

    node.declare_parameter('x', 0.0)
    node.declare_parameter('y', 0.0)
    node.declare_parameter('theta', 0.0)

    x = node.get_parameter('x').value
    y = node.get_parameter('y').value
    theta = node.get_parameter('theta').value

    if node.wait_for_server():
        node.send_goal(x, y, theta)
        rclpy.spin(node)
    else:
        node.get_logger().error('Nav2 action server not available')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
