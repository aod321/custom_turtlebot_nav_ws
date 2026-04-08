"""Workstation: launch RViz2 with the project default config.

Run on the workstation only. Requires:
  - workspace built and sourced
  - scripts/setup_workstation.sh sourced (sets DDS env vars)
  - RPi-side sensors already running (otherwise nothing to display)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_bringup = get_package_share_directory('custom_tb4_bringup')
    default_rviz = os.path.join(pkg_bringup, 'config', 'default.rviz')

    return LaunchDescription([
        DeclareLaunchArgument(
            'rviz_config',
            default_value=default_rviz,
            description='Path to RViz config file',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', LaunchConfiguration('rviz_config')],
            output='screen',
        ),
    ])
