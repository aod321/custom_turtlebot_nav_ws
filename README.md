# custom_turtlebot_nav_ws

Custom ROS2 workspace for a bare iRobot Create3 with manually-mounted RPLIDAR A1
and USB camera. Targets ROS2 Humble on a Raspberry Pi 4.

## Why this exists

Stock TurtleBot4 packages assume the standard sensor mount (RPLIDAR on the OAK-D
shell, OAK-D as the camera). This workspace adapts the stack for a custom
hardware build:

- **RPLIDAR A1** mounted on top of the bare Create3, 12 cm above base, 3 cm
  behind center, triangle marker pointing to the robot's left (yaw = -π/2).
- **USB camera** on an aluminum pole at the rear of the Create3, 42 cm above
  base, facing forward.

It does **not** modify any files in `/opt/ros/humble/`. Everything customized
lives in this workspace, so `apt upgrade` will not break it.

## Packages

| Package | Purpose |
|---------|---------|
| `custom_tb4_description` | URDF/xacro for the rplidar + camera mounts. Runs a secondary `robot_state_publisher` (`custom_extras_rsp`) that publishes the additional sensor TFs alongside the system Create3 RSP. |
| `custom_tb4_bringup` | Launch files for sensors, SLAM, navigation, and the full system. Bundles config overrides (camera calibration, etc.). |
| `custom_tb4_autonomy` | Python nodes: object detection (TFLite), patrol state machine, navigation goal sender, dock-aware teleop. |

## Hardware assumptions

- iRobot Create3 (firmware H.2.6 or compatible)
- Raspberry Pi 4 (8 GB) running Ubuntu 22.04 + ROS2 Humble
- Slamtec RPLIDAR A1 on `/dev/RPLIDAR` (udev rule), CH340 USB adapter
- USB webcam on `/dev/video0` (e.g., Realtek/Logitech UVC, 640x480 @ 15 FPS)
- TurtleBot4 systemd service (`turtlebot4.service`) running, providing the
  Create3 bridge and base `robot_state_publisher`

## Build

```bash
cd ~/custom_turtlebot_nav_ws
colcon build --symlink-install
source install/setup.bash
```

## Usage

The TurtleBot4 system service (`turtlebot4.service`) must already be running.
It provides the Create3 odom→base_link TF and the standard Create3 URDF.

### 1. SLAM (build a map)

```bash
ros2 launch custom_tb4_bringup slam.launch.py
# In another terminal: drive around with teleop
ros2 run custom_tb4_autonomy teleop  # press 'd' to undock, 'i/j/k/l/,' to drive
# When done, save the map:
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_environment
```

### 2. Navigation (use a saved map)

```bash
ros2 launch custom_tb4_bringup nav.launch.py \
  map:=/home/ubuntu/maps/my_environment.yaml
```

In RViz2, set Fixed Frame to `map`, then use **2D Pose Estimate** to set the
initial pose (matching where the robot actually is in the map). Then use
**2D Nav Goal** to send navigation targets.

### 3. Full system (nav + detection + patrol)

```bash
ros2 launch custom_tb4_bringup full_system.launch.py \
  map:=/home/ubuntu/maps/my_environment.yaml \
  enable_detection:=true \
  enable_patrol:=true \
  waypoints_file:=$(ros2 pkg prefix custom_tb4_autonomy)/share/custom_tb4_autonomy/config/waypoints.yaml
```

## Calibration / mounting tweaks

If you change the physical mounting of the LIDAR or camera, edit the joint
origins in `custom_tb4_description/urdf/custom_extras.urdf.xacro` and rebuild.

The RPLIDAR's yaw (`-1.5708` = -90°) corresponds to the triangle marker
pointing to the robot's left side. If your unit is mounted differently, adjust
this value (positive = counterclockwise viewed from above).

## Known issues / gotchas

- **Don't kill `turtlebot4.service` processes.** Killing the system
  `robot_state_publisher` breaks the TF tree and requires a Create3 reboot to
  recover.
- **DDS RELIABLE QoS scaling.** Create3 publishes `/tf` with RELIABLE QoS.
  Starting many TF subscribers (AMCL + Nav2) over a short time can stress
  FastDDS matching. If a freshly-spawned node can't see `odom→base_link`, wait
  10–15 s before testing.
- **`auto_standby` on RPLIDAR.** The stock turtlebot4 launch sets
  `auto_standby: True`, which often leaves the publisher inactive. Our launch
  forces `False`.
- **Map borders.** When building the map, drive at least 1–2 m past the
  charging dock in every direction so the costmap has padding around the
  start position. Otherwise Nav2 may report `worldToMap failed` once the
  robot leaves the dock.

## Layout

```
custom_turtlebot_nav_ws/
└── src/
    ├── custom_tb4_description/
    │   ├── package.xml
    │   ├── CMakeLists.txt
    │   ├── urdf/custom_extras.urdf.xacro
    │   └── launch/description.launch.py
    ├── custom_tb4_bringup/
    │   ├── package.xml
    │   ├── CMakeLists.txt
    │   ├── launch/
    │   │   ├── rplidar.launch.py
    │   │   ├── camera.launch.py
    │   │   ├── sensors.launch.py
    │   │   ├── slam.launch.py
    │   │   ├── nav.launch.py
    │   │   └── full_system.launch.py
    │   └── config/camera_calibration.yaml
    └── custom_tb4_autonomy/
        ├── package.xml
        ├── setup.py
        ├── custom_tb4_autonomy/
        │   ├── object_detector_node.py
        │   ├── patrol_node.py
        │   ├── nav_goal_sender.py
        │   ├── tf_broadcaster.py
        │   └── tb4_teleop.py
        └── config/waypoints.yaml
```
