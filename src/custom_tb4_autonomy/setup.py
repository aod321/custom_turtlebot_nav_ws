import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'custom_tb4_autonomy'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ubuntu',
    maintainer_email='ubuntu@todo.todo',
    description='Custom TurtleBot4 autonomy: detection, patrol, teleop',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'object_detector = custom_tb4_autonomy.object_detector_node:main',
            'patrol = custom_tb4_autonomy.patrol_node:main',
            'nav_goal_sender = custom_tb4_autonomy.nav_goal_sender:main',
            'tf_broadcaster = custom_tb4_autonomy.tf_broadcaster:main',
            'teleop = custom_tb4_autonomy.tb4_teleop:main',
        ],
    },
)
