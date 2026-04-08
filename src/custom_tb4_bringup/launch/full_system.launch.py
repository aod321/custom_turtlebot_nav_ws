"""Full system: sensors + nav + (optional) object detection + (optional) patrol.

Usage:
    # Just navigation
    ros2 launch custom_tb4_bringup full_system.launch.py

    # Navigation + detection
    ros2 launch custom_tb4_bringup full_system.launch.py enable_detection:=true

    # Navigation + detection + patrol
    ros2 launch custom_tb4_bringup full_system.launch.py \\
        enable_detection:=true enable_patrol:=true \\
        waypoints_file:=/path/to/waypoints.yaml
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_bringup = get_package_share_directory('custom_tb4_bringup')

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value='/home/ubuntu/maps/my_environment.yaml'),
        DeclareLaunchArgument('enable_detection', default_value='false'),
        DeclareLaunchArgument('enable_patrol', default_value='false'),
        DeclareLaunchArgument('model_path',
            default_value='/home/ubuntu/tb4_models/ssd_mobilenet_v2.tflite'),
        DeclareLaunchArgument('label_path',
            default_value='/home/ubuntu/tb4_models/labelmap.txt'),
        DeclareLaunchArgument('waypoints_file', default_value=''),
        DeclareLaunchArgument('observe_duration', default_value='3.0'),

        # Nav stack (includes sensors)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_bringup, 'launch', 'nav.launch.py')),
            launch_arguments={'map': LaunchConfiguration('map')}.items()),

        # Object detector (optional)
        Node(
            condition=IfCondition(LaunchConfiguration('enable_detection')),
            package='custom_tb4_autonomy',
            executable='object_detector',
            name='object_detector',
            output='screen',
            parameters=[{
                'model_path': LaunchConfiguration('model_path'),
                'label_path': LaunchConfiguration('label_path'),
                'confidence_threshold': 0.5,
                'inference_rate': 3.0,
            }],
        ),

        # Patrol node (optional)
        Node(
            condition=IfCondition(LaunchConfiguration('enable_patrol')),
            package='custom_tb4_autonomy',
            executable='patrol',
            name='patrol_node',
            output='screen',
            parameters=[{
                'waypoints_file': LaunchConfiguration('waypoints_file'),
                'observe_duration': LaunchConfiguration('observe_duration'),
            }],
        ),
    ])
