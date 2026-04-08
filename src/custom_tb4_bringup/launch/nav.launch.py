"""Navigation mode: sensors + AMCL + Nav2.

Requires a pre-built map. Usage:
    ros2 launch custom_tb4_bringup nav.launch.py map:=/home/ubuntu/maps/my_environment.yaml
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_bringup = get_package_share_directory('custom_tb4_bringup')
    pkg_tb4_nav = get_package_share_directory('turtlebot4_navigation')

    map_arg = DeclareLaunchArgument(
        'map',
        default_value='/home/ubuntu/maps/my_environment.yaml',
        description='Full path to map YAML file')

    return LaunchDescription([
        map_arg,

        # Sensors
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_bringup, 'launch', 'sensors.launch.py'))),

        # AMCL localization
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_tb4_nav, 'launch', 'localization.launch.py')),
            launch_arguments={'map': LaunchConfiguration('map')}.items()),

        # Nav2
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_tb4_nav, 'launch', 'nav2.launch.py'))),
    ])
