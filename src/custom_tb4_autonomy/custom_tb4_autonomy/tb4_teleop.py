"""TurtleBot4 teleop with undock/dock support.

Keys:
    i/,     : forward/backward
    j/l     : turn left/right
    u/o     : forward-left/forward-right
    m/.     : backward-left/backward-right
    k       : stop
    q/z     : increase/decrease speed
    d       : undock
    f       : dock
    Ctrl+C  : quit
"""
import sys
import termios
import tty

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import Twist

try:
    from irobot_create_msgs.action import Undock, Dock
    HAS_CREATE_MSGS = True
except ImportError:
    HAS_CREATE_MSGS = False

BINDINGS = {
    'i': (1, 0, 0, 0),   # forward
    'o': (1, 0, 0, -1),  # forward-right
    'j': (0, 0, 0, 1),   # turn left
    'l': (0, 0, 0, -1),  # turn right
    'u': (1, 0, 0, 1),   # forward-left
    ',': (-1, 0, 0, 0),  # backward
    '.': (-1, 0, 0, 1),  # backward-right
    'm': (-1, 0, 0, -1), # backward-left
    'k': (0, 0, 0, 0),   # stop
}

HELP = """
---------------------------
TurtleBot4 Teleop
---------------------------
   u    i    o
   j    k    l
   m    ,    .

i/,  : forward/backward
j/l  : turn left/right
k    : stop
q/z  : +/- speed
d    : undock
f    : dock
Ctrl+C : quit
---------------------------
"""


def get_key(settings):
    tty.setraw(sys.stdin.fileno())
    key = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def main():
    settings = termios.tcgetattr(sys.stdin)

    rclpy.init()
    node = rclpy.create_node('tb4_teleop')
    pub = node.create_publisher(Twist, '/cmd_vel', 10)

    undock_client = None
    dock_client = None
    if HAS_CREATE_MSGS:
        undock_client = ActionClient(node, Undock, '/undock')
        dock_client = ActionClient(node, Dock, '/dock')

    speed = 0.15
    turn = 0.5

    print(HELP)
    print('Speed: {:.2f}  Turn: {:.2f}'.format(speed, turn))

    try:
        while True:
            key = get_key(settings)

            if key == '\x03':  # Ctrl+C
                break

            if key == 'q':
                speed = min(speed + 0.05, 0.5)
                turn = min(turn + 0.1, 2.0)
                print('Speed: {:.2f}  Turn: {:.2f}'.format(speed, turn))
                continue

            if key == 'z':
                speed = max(speed - 0.05, 0.05)
                turn = max(turn - 0.1, 0.1)
                print('Speed: {:.2f}  Turn: {:.2f}'.format(speed, turn))
                continue

            if key == 'd':
                if undock_client and undock_client.wait_for_server(timeout_sec=3.0):
                    print('Undocking...')
                    future = undock_client.send_goal_async(Undock.Goal())
                    rclpy.spin_until_future_complete(node, future, timeout_sec=5.0)
                    handle = future.result()
                    if handle and handle.accepted:
                        rf = handle.get_result_async()
                        rclpy.spin_until_future_complete(node, rf, timeout_sec=30.0)
                        print('Undock done!')
                    else:
                        print('Undock rejected')
                else:
                    print('Undock not available')
                continue

            if key == 'f':
                if dock_client and dock_client.wait_for_server(timeout_sec=3.0):
                    print('Docking...')
                    future = dock_client.send_goal_async(Dock.Goal())
                    rclpy.spin_until_future_complete(node, future, timeout_sec=5.0)
                    handle = future.result()
                    if handle and handle.accepted:
                        rf = handle.get_result_async()
                        rclpy.spin_until_future_complete(node, rf, timeout_sec=60.0)
                        print('Dock done!')
                    else:
                        print('Dock rejected')
                else:
                    print('Dock not available')
                continue

            if key in BINDINGS:
                x, y, z, th = BINDINGS[key]
                twist = Twist()
                twist.linear.x = x * speed
                twist.linear.y = y * speed
                twist.angular.z = th * turn
                pub.publish(twist)
            else:
                # Unknown key, stop
                twist = Twist()
                pub.publish(twist)

    except Exception as e:
        print(e)
    finally:
        # Stop
        twist = Twist()
        pub.publish(twist)
        node.destroy_node()
        rclpy.shutdown()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)


if __name__ == '__main__':
    main()
