"""Launch a secondary robot_state_publisher for our custom sensor extras.

This RSP is named 'custom_extras_rsp' so it doesn't conflict with the system's
Create3 RSP. It publishes only rplidar_link, camera_link, and pole_link as
static transforms from base_link.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_dir = get_package_share_directory('custom_tb4_description')
    xacro_file = os.path.join(pkg_dir, 'urdf', 'custom_extras.urdf.xacro')

    robot_description = ParameterValue(
        Command(['xacro ', xacro_file]),
        value_type=str,
    )

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='custom_extras_rsp',
            output='screen',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': False,
                'publish_frequency': 10.0,
            }],
            remappings=[
                ('/robot_description', '/custom_extras_description'),
            ],
        ),
    ])
