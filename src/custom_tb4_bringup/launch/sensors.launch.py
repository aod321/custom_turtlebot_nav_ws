"""Launch all sensors: RPLIDAR + USB camera + custom URDF extras (rplidar/camera TFs)."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    pkg_bringup = get_package_share_directory('custom_tb4_bringup')
    pkg_description = get_package_share_directory('custom_tb4_description')

    return LaunchDescription([
        # 1. Custom URDF extras (publishes rplidar_link, camera_link TFs)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_description, 'launch', 'description.launch.py'))),

        # 2. RPLIDAR
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_bringup, 'launch', 'rplidar.launch.py'))),

        # 3. USB camera
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_bringup, 'launch', 'camera.launch.py'))),
    ])
