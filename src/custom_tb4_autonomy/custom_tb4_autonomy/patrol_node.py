"""Patrol node: navigate through waypoints and observe detections at each."""
import yaml
from enum import Enum, auto

from custom_tb4_autonomy.nav_goal_sender import euler_to_quaternion


class PatrolState(Enum):
    IDLE = auto()
    NAVIGATING = auto()
    OBSERVING = auto()
    DONE = auto()


def load_waypoints(yaml_path):
    """Load waypoints from YAML file.

    Expected format:
        waypoints:
          kitchen:
            x: 1.0
            y: 2.0
            theta: 1.57
          living_room:
            x: 3.0
            y: -1.0
            theta: 0.0
    Returns list of (name, x, y, theta) tuples.
    """
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    if not data or 'waypoints' not in data:
        return []
    wps = []
    for name, coords in data['waypoints'].items():
        wps.append((
            str(name),
            float(coords.get('x', 0.0)),
            float(coords.get('y', 0.0)),
            float(coords.get('theta', 0.0)),
        ))
    return wps


class PatrolStateMachine:
    """Pure state machine for patrol logic (no ROS2 dependency)."""

    def __init__(self, waypoints, observe_duration=3.0):
        self.waypoints = waypoints
        self.observe_duration = observe_duration
        self.state = PatrolState.IDLE
        self.current_index = 0
        self.detections_log = []
        self.observe_timer = 0.0

    @property
    def current_waypoint(self):
        if self.current_index < len(self.waypoints):
            return self.waypoints[self.current_index]
        return None

    @property
    def is_done(self):
        return self.state == PatrolState.DONE

    def start(self):
        if not self.waypoints:
            self.state = PatrolState.DONE
            return None
        self.state = PatrolState.NAVIGATING
        self.current_index = 0
        return self.current_waypoint

    def on_navigation_complete(self, success):
        """Called when Nav2 reports goal reached or failed."""
        wp = self.current_waypoint
        if success:
            self.state = PatrolState.OBSERVING
            self.observe_timer = 0.0
            return ('observe', wp)
        else:
            # Skip failed waypoint, move to next
            return self._advance()

    def on_observe_tick(self, dt, detections=None):
        """Called periodically during observation.

        Args:
            dt: time elapsed since last tick (seconds)
            detections: list of detection dicts from this tick

        Returns:
            ('observing', wp) if still observing
            ('navigate', wp) if moving to next waypoint
            ('done', None) if all waypoints visited
        """
        if self.state != PatrolState.OBSERVING:
            return ('idle', None)

        self.observe_timer += dt
        wp = self.current_waypoint

        if detections:
            self.detections_log.append({
                'waypoint': wp[0],
                'detections': detections,
            })

        if self.observe_timer >= self.observe_duration:
            return self._advance()

        return ('observing', wp)

    def _advance(self):
        """Move to next waypoint or finish."""
        self.current_index += 1
        if self.current_index >= len(self.waypoints):
            self.state = PatrolState.DONE
            return ('done', None)
        self.state = PatrolState.NAVIGATING
        return ('navigate', self.current_waypoint)

    def get_report(self):
        """Return summary of detections at all visited waypoints."""
        return list(self.detections_log)


# --- ROS2 Node ---

def make_patrol_node_class():
    import rclpy
    from rclpy.node import Node
    from rclpy.action import ActionClient
    from nav2_msgs.action import NavigateToPose
    from geometry_msgs.msg import PoseStamped
    from vision_msgs.msg import Detection2DArray

    class PatrolNode(Node):

        def __init__(self):
            super().__init__('patrol_node')

            self.declare_parameter('waypoints_file', '')
            self.declare_parameter('observe_duration', 3.0)

            wp_file = self.get_parameter('waypoints_file').value
            obs_dur = self.get_parameter('observe_duration').value

            waypoints = load_waypoints(wp_file) if wp_file else []
            self.sm = PatrolStateMachine(waypoints, obs_dur)

            self._nav_client = ActionClient(
                self, NavigateToPose, '/navigate_to_pose')
            self._latest_detections = []

            self.create_subscription(
                Detection2DArray, '/detections', self._det_cb, 10)

            self._observe_timer = None
            self.get_logger().info(
                'Patrol node ready with {} waypoints'.format(len(waypoints)))

        def start_patrol(self):
            if not self._nav_client.wait_for_server(timeout_sec=10.0):
                self.get_logger().error('Nav2 not available')
                return
            wp = self.sm.start()
            if wp:
                self.get_logger().info(
                    'Starting patrol, first waypoint: {}'.format(wp[0]))
                self._send_nav_goal(wp)
            else:
                self.get_logger().warn('No waypoints to patrol')

        def _send_nav_goal(self, wp):
            name, x, y, theta = wp
            goal = NavigateToPose.Goal()
            goal.pose = PoseStamped()
            goal.pose.header.frame_id = 'map'
            goal.pose.header.stamp = self.get_clock().now().to_msg()
            goal.pose.pose.position.x = x
            goal.pose.pose.position.y = y
            w, qx, qy, qz = euler_to_quaternion(theta)
            goal.pose.pose.orientation.w = w
            goal.pose.pose.orientation.x = qx
            goal.pose.pose.orientation.y = qy
            goal.pose.pose.orientation.z = qz

            self.get_logger().info(
                'Navigating to {} ({:.1f}, {:.1f})'.format(name, x, y))
            future = self._nav_client.send_goal_async(goal)
            future.add_done_callback(self._goal_response_cb)

        def _goal_response_cb(self, future):
            handle = future.result()
            if not handle.accepted:
                self.get_logger().warn('Goal rejected')
                self._handle_nav_result(False)
                return
            handle.get_result_async().add_done_callback(
                self._nav_result_cb)

        def _nav_result_cb(self, future):
            status = future.result().status
            success = (status == 4)  # STATUS_SUCCEEDED
            self._handle_nav_result(success)

        def _handle_nav_result(self, success):
            result = self.sm.on_navigation_complete(success)
            action, wp = result

            if action == 'observe':
                self.get_logger().info(
                    'Arrived at {}, observing...'.format(wp[0]))
                self._observe_timer = self.create_timer(
                    0.5, self._observe_tick)
            else:
                self._process_action(action, wp)

        def _observe_tick(self):
            dets = list(self._latest_detections)
            self._latest_detections = []
            result = self.sm.on_observe_tick(0.5, dets if dets else None)
            action, wp = result

            if action != 'observing':
                if self._observe_timer:
                    self._observe_timer.cancel()
                    self._observe_timer = None
                self._process_action(action, wp)

        def _process_action(self, action, wp):
            if action == 'navigate':
                self._send_nav_goal(wp)
            elif action == 'done':
                report = self.sm.get_report()
                self.get_logger().info(
                    'Patrol complete! Detections at {} waypoints'.format(
                        len(report)))
                for entry in report:
                    self.get_logger().info(
                        '  {}: {} detections'.format(
                            entry['waypoint'], len(entry['detections'])))

        def _det_cb(self, msg):
            dets = []
            for d in msg.detections:
                if d.results:
                    dets.append({
                        'class_id': d.results[0].hypothesis.class_id,
                        'score': d.results[0].hypothesis.score,
                    })
            if dets:
                self._latest_detections.extend(dets)

    return PatrolNode


def main(args=None):
    import rclpy
    rclpy.init(args=args)
    cls = make_patrol_node_class()
    node = cls()
    node.start_patrol()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
