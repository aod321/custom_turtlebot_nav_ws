"""Launch the canonical robot_state_publisher + joint_state_publisher
for our custom Create3 + sensors URDF.

This is the SOLE robot description publisher. It REPLACES the system
turtlebot4 standard description (which assumes a shell + standard sensor
mounts that we don't have). For this replacement to take effect, the
system's standard.launch.py must NOT include its own description launch
— see scripts/install_description_override.sh.

Publishes:
  - /robot_description (URDF as String, TRANSIENT_LOCAL)
  - /tf_static (all fixed joints in our URDF, including Create3 base)
  - /joint_states (from joint_state_publisher for any non-fixed joints)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_dir = get_package_share_directory('custom_tb4_description')
    xacro_file = os.path.join(pkg_dir, 'urdf', 'custom_robot.urdf.xacro')

    robot_description = ParameterValue(
        Command(['xacro ', xacro_file]),
        value_type=str,
    )

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': False,
                'publish_frequency': 10.0,
            }],
        ),
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': False,
            }],
        ),
    ])
