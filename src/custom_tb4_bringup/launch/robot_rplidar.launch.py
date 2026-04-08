"""Launch RPLIDAR with our custom parameters.

Differs from turtlebot4_bringup's rplidar.launch.py:
  - auto_standby: False (the default True causes scan publisher to not start)
  - inverted: False (matches our physical mounting)
  - frame_id: rplidar_link (matches custom_tb4_description URDF)
"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='rplidar_ros',
            executable='rplidar_composition',
            name='rplidar_composition',
            output='screen',
            parameters=[{
                'serial_port': '/dev/RPLIDAR',
                'serial_baudrate': 115200,
                'frame_id': 'rplidar_link',
                'inverted': False,
                'angle_compensate': True,
                'auto_standby': False,
            }],
        ),
    ])
