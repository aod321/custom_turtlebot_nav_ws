# CLAUDE.md — context for AI agents

This file is automatically loaded by Claude Code (and other AI assistants
following the CLAUDE.md convention) when working in this repository. It
captures the gotchas and decisions that aren't obvious from reading the
code.

## Project shape

- **Multi-machine ROS2 Humble project.** RPi runs sensors + Nav2/SLAM.
  Workstation runs RViz + ML. Create3 is the diff-drive base.
- **DDS topology:** FastDDS Discovery Server on the RPi, all participants
  use `ROS_DOMAIN_ID=64`, the workstation uses `ROS_SUPER_CLIENT=True`.
- **Spec:** `docs/specs/2026-04-08-multi-machine-deployment-design.md`
- **Implementation plan:** `docs/plans/2026-04-08-multi-machine-deployment.md`

## Hard rules

1. **Never modify files under `/opt/ros/humble/`.** All customizations live
   in this workspace. The only exception is `/etc/turtlebot4/setup.bash`,
   which must be edited as part of one-time commissioning.
2. **Never kill the `turtlebot4.service` processes.** Killing the system
   `robot_state_publisher` or `turtlebot4_node` breaks the TF tree and
   typically requires a Create3 reboot to recover.
3. **Don't use `sshpass` SSH commands** in examples or new scripts. The
   workstation has `ssh rpi` configured already (key + alias).
4. **Don't auto-generate complex `.rviz` configs.** They've caused segfaults
   in the past. Provide a minimal default and let the user add displays.

## Known gotchas (don't relearn these)

| Symptom | Root cause | Fix |
|---|---|---|
| Many DDS subscribers cause Create3 to drop `/tf` messages | Create3 publishes `/tf` RELIABLE; matching scales linearly with subscribers | Use Discovery Server + super-client mode on workstation |
| Restarting SLAM/Nav2 a few times stalls Create3's `/tf` writer until physical reboot | Phantom RELIABLE reader proxies pile up on Create3 faster than DDS liveliness reaps them | `setup_robot.sh`/`setup_workstation.sh` set `FASTRTPS_DEFAULT_PROFILES_FILE=scripts/fastdds_qos_override.xml` which downgrades `/tf` readers to BEST_EFFORT (writer stops tracking unacked samples) |
| `ros2 topic echo` fails but Python rclpy subscriber works | ros2 daemon cache stale | `ros2 daemon stop && ros2 daemon start` |
| RPLIDAR `/scan` Publisher count = 0 | Stock turtlebot4 launch sets `auto_standby: True` | Our `robot_rplidar.launch.py` forces `False` |
| AMCL drops every scan with "timestamp earlier than transform cache" | static_transform_publisher restarted with newer timestamp than scans | Don't restart static TF publishers; if you must, also restart AMCL |
| Nav2 ABORTED with `worldToMap failed` | Robot is outside map bounds (often because dock is at map edge) | Build a larger map with more padding around the dock |
| RViz crashes on startup with auto-loaded config | RViz Image / RobotModel display interaction with NVIDIA driver | Use minimal `default.rviz` (TF + LaserScan + Map only); add other displays manually |
| RPi's `source /opt/ros/humble/setup.bash` works in bash but not zsh | zsh doesn't expand `BASH_SOURCE` the same way | Use `source /opt/ros/humble/setup.zsh` or wrap in `bash -c '...'` |
| `ros2 launch <pkg> robot/foo.launch.py` not found despite file existing | `ros2 launch` searches by filename, ignores subdirectory | Use flat file naming with `robot_` / `workstation_` prefix |

## Charging dock position

After SLAM, the dock is at the **map origin** (the SLAM-saved `origin` field
of the map yaml typically translates the dock coordinate to (0, 0, yaw=0)
in the map frame). When setting the AMCL initial pose at startup, use
`(0, 0, yaw=0)`. Build the map by driving at least 1–2 m past the dock in
every direction so Nav2 has costmap padding.

## Connecting to the robot

```bash
ssh rpi                                # alias is preconfigured
cd ~/custom_turtlebot_nav_ws
source install/setup.bash
source scripts/setup_robot.sh
```

## How to add a new launch file

- If it runs on the RPi: name it `robot_<purpose>.launch.py` and put it in
  `src/custom_tb4_bringup/launch/`.
- If it runs on the workstation: name it `workstation_<purpose>.launch.py`.
- Document the assumed prerequisites (sensors running? sourced setup script?)
  in the docstring at the top of the file.

## How to debug

Use ROS2 CLI tools first, not ad-hoc Python:
- `ros2 node list` / `ros2 node info <node>`
- `ros2 topic list` / `ros2 topic info <topic> --verbose` / `ros2 topic hz <topic>`
- `ros2 run tf2_ros tf2_echo <parent> <child>`
- `scripts/check_network.sh` for network diagnostics
- `scripts/smoke_test.sh` for end-to-end handoff verification
