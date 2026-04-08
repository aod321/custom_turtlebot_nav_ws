"""Workstation: launch object detector (TFLite ML).

Run on the workstation. Requires:
  - workspace built and sourced
  - scripts/setup_workstation.sh sourced
  - TFLite model file at ~/tb4_models/ssd_mobilenet_v2.tflite
  - RPi-side camera publishing /camera/image_raw/compressed
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    home = os.path.expanduser('~')
    return LaunchDescription([
        DeclareLaunchArgument(
            'model_path',
            default_value=os.path.join(home, 'tb4_models', 'ssd_mobilenet_v2.tflite'),
        ),
        DeclareLaunchArgument(
            'label_path',
            default_value=os.path.join(home, 'tb4_models', 'labelmap.txt'),
        ),
        DeclareLaunchArgument('confidence_threshold', default_value='0.5'),
        DeclareLaunchArgument('inference_rate', default_value='3.0'),

        Node(
            package='custom_tb4_autonomy',
            executable='object_detector',
            name='object_detector',
            output='screen',
            parameters=[{
                'model_path': LaunchConfiguration('model_path'),
                'label_path': LaunchConfiguration('label_path'),
                'confidence_threshold': LaunchConfiguration('confidence_threshold'),
                'inference_rate': LaunchConfiguration('inference_rate'),
            }],
        ),
    ])
