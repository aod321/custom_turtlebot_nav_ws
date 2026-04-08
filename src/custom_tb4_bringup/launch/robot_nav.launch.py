"""Navigation mode: sensors + AMCL + Nav2.

Requires a pre-built map. Usage:
    ros2 launch custom_tb4_bringup robot_nav.launch.py map:=/home/ubuntu/maps/my_environment.yaml
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

    localization_params = os.path.join(pkg_bringup, 'config', 'localization.yaml')
    nav2_params = os.path.join(pkg_bringup, 'config', 'nav2.yaml')

    return LaunchDescription([
        map_arg,

        # Sensors
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_bringup, 'launch', 'robot_sensors.launch.py'))),

        # AMCL localization (project-local copy of turtlebot4's tuned params)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_tb4_nav, 'launch', 'localization.launch.py')),
            launch_arguments={
                'map': LaunchConfiguration('map'),
                'params': localization_params,
            }.items()),

        # Nav2 (project-local copy of turtlebot4's tuned params)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_tb4_nav, 'launch', 'nav2.launch.py')),
            launch_arguments={'params_file': nav2_params}.items()),
    ])
