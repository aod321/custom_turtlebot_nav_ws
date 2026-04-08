"""Launch USB camera with v4l2_camera, remapped to /camera/* namespace."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('custom_tb4_bringup')
    default_calib = os.path.join(pkg_dir, 'config', 'camera_calibration.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('video_device', default_value='/dev/video0'),
        DeclareLaunchArgument('camera_info_url',
                              default_value='file://' + default_calib),

        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='usb_camera',
            output='screen',
            parameters=[{
                'video_device': LaunchConfiguration('video_device'),
                'pixel_format': 'MJPG',
                'image_size': [640, 480],
                'camera_frame_id': 'camera_link',
                'camera_info_url': LaunchConfiguration('camera_info_url'),
            }],
            remappings=[
                ('/image_raw', '/camera/image_raw'),
                ('/camera_info', '/camera/camera_info'),
            ],
        ),
    ])
