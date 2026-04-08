# Troubleshooting

Symptom-indexed cookbook for the custom_turtlebot_nav_ws stack.

## DDS / discovery

### `ros2 node list` shows nothing or only my workstation's nodes

1. Verify the discovery server is up on the RPi:
   ```bash
   ssh rpi 'systemctl status fastdds_discovery_server'
   ```
2. Verify the server is listening on the right port:
   ```bash
   nc -zvw 2 192.168.111.230 11811
   ```
3. Verify your workstation env:
   ```bash
   echo $ROS_DOMAIN_ID $ROS_DISCOVERY_SERVER $ROS_SUPER_CLIENT
   # expect: 64  192.168.111.230:11811  True
   ```
4. Refresh the daemon:
   ```bash
   ros2 daemon stop && ros2 daemon start
   ```

### `ros2 topic echo` says "topic does not appear to be published yet" but Python subscribers work fine

The ros2 daemon cache is stale.
```bash
ros2 daemon stop && ros2 daemon start
```

### Create3's nodes (motion_control, robot_state) don't show up

1. Check the Create3 web UI (`http://192.168.186.2`) is reachable from the RPi.
2. Verify Create3's App Config has `ROS_DOMAIN_ID=64` and discovery server
   `192.168.186.3:11811` enabled.
3. Restart the Create3 application from its web UI.
4. Wait 2–3 minutes for Create3 to fully boot before testing again.

## Sensors

### `/scan` has no data

1. Is the LIDAR powered? The motor must be visibly spinning.
2. Is `rplidar_composition` running on the RPi?
   ```bash
   ssh rpi 'ps aux | grep rplidar_composition | grep -v grep'
   ```
3. If the process is running but `/scan` `Publisher count: 0`, the LIDAR
   was likely off when the node started. Restart it:
   ```bash
   ssh rpi
   pkill -f rplidar_composition
   ros2 launch custom_tb4_bringup robot_sensors.launch.py
   ```
4. If the serial port is locked after multiple restarts, USB-reset the
   CH340 adapter:
   ```bash
   for dev in /sys/bus/usb/devices/*/; do
     vid=$(cat "$dev/idVendor" 2>/dev/null)
     pid=$(cat "$dev/idProduct" 2>/dev/null)
     if [ "$vid" = "1a86" ] && [ "$pid" = "7523" ]; then
       devpath=$(basename "$dev")
       sudo sh -c "echo 0 > /sys/bus/usb/devices/$devpath/authorized"
       sleep 1
       sudo sh -c "echo 1 > /sys/bus/usb/devices/$devpath/authorized"
     fi
   done
   ```

### Camera has no data on `/camera/image_raw/compressed`

1. `ros-humble-image-transport-plugins` installed on the RPi?
   ```bash
   ssh rpi 'dpkg -l | grep image-transport-plugins'
   ```
2. Is `v4l2_camera_node` running?
3. Try the raw topic to isolate: `ros2 topic hz /camera/image_raw`. If raw
   has data but compressed doesn't, the plugin isn't loaded.

## SLAM / Nav2

### slam_toolbox / AMCL: `Message Filter dropping message: discarding because the queue is full`

The TF chain `rplidar_link → base_link → odom` is incomplete. Check that
both `custom_extras_rsp` and the Create3 system RSP are running. If you
just restarted a static TF publisher, restart the slam/amcl node too.

### slam_toolbox / AMCL: `timestamp earlier than all the data in the transform cache`

A TF publisher restarted with a newer wall-clock time than the buffered
scans. Restart slam/amcl to flush its message filter queue.

### Nav2 returns ABORTED with `worldToMap failed`

The robot's current position is outside the costmap. This usually means
the saved map is too small around the dock area. Rebuild the map and drive
1–2 m past the dock in every direction before saving.

### Nav2 returns ABORTED with `failed to create plan` and `Trajectory Hits Obstacle`

AMCL localization is wrong, so the robot's costmap position doesn't match
reality. Fix in RViz: use **2D Pose Estimate** to click the actual position
on the map. Then clear the costmaps:
```bash
ros2 service call /global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap "{}"
ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap "{}"
```

### AMCL `lifecycle_manager_localization: Failed to bring up all requested nodes`

Lifecycle manager race condition (`transition invoked while in transition`).
Just restart it:
```bash
ssh rpi 'pkill -f localization.launch'
ros2 launch custom_tb4_bringup robot_nav.launch.py map:=/home/ubuntu/maps/my_environment.yaml
```

## RViz / visualization

### RViz crashes on startup

We've seen this with auto-loaded `.rviz` configs that include `RobotModel`
or `Image` displays. Use the minimal `default.rviz` (TF + LaserScan + Map
only) and add other displays manually.

### RViz shows the laser scan but not the map

Check the Map display's `Durability Policy` is **Transient Local** and
`Reliability Policy` is **Reliable** (the map server uses TRANSIENT_LOCAL).

## Workstation environment

### `source /opt/ros/humble/setup.bash` fails on the workstation

The workstation uses zsh; `setup.bash` references `BASH_SOURCE` which zsh
handles differently. Either:
- Use `source /opt/ros/humble/setup.zsh` instead, or
- Wrap the command: `bash -c 'source /opt/ros/humble/setup.bash && ...'`

Also `conda deactivate` first if a conda env is active — Python 3.13 from
conda conflicts with ROS2's Python 3.10.
