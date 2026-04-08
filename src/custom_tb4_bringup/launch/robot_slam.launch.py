"""SLAM mode: sensors + slam_toolbox.

Use this for building maps. The system Create3 RSP must already be running
(via turtlebot4 service). Run:
    ros2 launch custom_tb4_bringup robot_slam.launch.py
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    pkg_bringup = get_package_share_directory('custom_tb4_bringup')
    pkg_tb4_nav = get_package_share_directory('turtlebot4_navigation')

    slam_params = os.path.join(pkg_bringup, 'config', 'slam.yaml')

    return LaunchDescription([
        # Sensors (rplidar + camera + custom URDF TFs)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_bringup, 'launch', 'robot_sensors.launch.py'))),

        # SLAM Toolbox with project-local copy of turtlebot4's tuned params
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_tb4_nav, 'launch', 'slam.launch.py')),
            launch_arguments={'params': slam_params}.items()),
    ])
