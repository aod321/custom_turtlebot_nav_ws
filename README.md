# custom_turtlebot_nav_ws

ROS2 Humble workspace for a bare iRobot Create3 + RPLIDAR A1 + USB camera,
deployed across a Raspberry Pi 4 (robot side) and a dedicated workstation
(ML inference + visualization).

## System topology

```
Create3 (192.168.186.2)            Workstation (5GHz WiFi)
   |                                  |
   | usb0                             | wlan0
   |                                  |
   +------- RPi 4 (192.168.111.230) --+
              ROS_DOMAIN_ID=64
              FastDDS discovery server :11811
```

All three machines share `ROS_DOMAIN_ID=64` and connect through a FastDDS
discovery server running on the RPi. The workstation uses super-client mode
so it doesn't disturb Create3's DDS state.

See `docs/specs/2026-04-08-multi-machine-deployment-design.md` for the
architecture rationale.

## Who are you?

| Role             | On which machine | Purpose                                |
|------------------|------------------|----------------------------------------|
| Robot maintainer | RPi (`ssh rpi`)  | Start sensors / SLAM / Nav2, edit URDF |
| ML / algorithm   | Workstation      | Run object_detector, tune ML models    |
| Mission / viz    | Workstation      | RViz, send goals, write task nodes     |

## Quick start

### "I want to connect this robot from the workstation"

```bash
cd ~/code/custom_turtlebot_nav_ws
colcon build --symlink-install   # only if not built
source install/setup.bash
source scripts/setup_workstation.sh

# Verify the link end-to-end
./scripts/smoke_test.sh

# Then bring up RViz (and optionally the ML inference)
ros2 launch custom_tb4_bringup workstation_viz.launch.py
ros2 launch custom_tb4_bringup workstation_ml.launch.py     # in another terminal
```

### "I want to (re)start sensors / SLAM / Nav2 on the RPi"

```bash
ssh rpi
cd ~/custom_turtlebot_nav_ws
source install/setup.bash
source scripts/setup_robot.sh

# Pick one mode:
ros2 launch custom_tb4_bringup robot_sensors.launch.py    # sensors only
ros2 launch custom_tb4_bringup robot_slam.launch.py       # sensors + SLAM
ros2 launch custom_tb4_bringup robot_nav.launch.py \
     map:=/home/ubuntu/maps/my_environment.yaml           # sensors + AMCL + Nav2
ros2 launch custom_tb4_bringup robot_full.launch.py \
     map:=/home/ubuntu/maps/my_environment.yaml \
     enable_detection:=true enable_patrol:=true           # nav + ML + patrol
```

## Build

```bash
cd ~/code/custom_turtlebot_nav_ws       # or ~/custom_turtlebot_nav_ws on RPi
colcon build --symlink-install
source install/setup.bash
```

## Packages

| Package | Purpose |
|---------|---------|
| `custom_tb4_description` | URDF/xacro for the rplidar + camera mounts. Runs a secondary `robot_state_publisher` (`custom_extras_rsp`) alongside the system Create3 RSP. |
| `custom_tb4_bringup` | Launch files (prefixed `robot_*` and `workstation_*`) and shared config (camera calibration, default RViz). |
| `custom_tb4_autonomy` | Python nodes: `object_detector`, `patrol`, `nav_goal_sender`, `tf_broadcaster`, `teleop`. |

## Launch file naming

Launch files are flat in `src/custom_tb4_bringup/launch/` and prefixed by
where they run:

| Prefix | Where to run | Example |
|---|---|---|
| `robot_*.launch.py` | RPi (`ssh rpi`) | `robot_sensors.launch.py`, `robot_slam.launch.py` |
| `workstation_*.launch.py` | Workstation | `workstation_viz.launch.py`, `workstation_ml.launch.py` |

## One-time commissioning (only when setting up a new robot)

See `docs/setup_new_robot.md` for the full checklist.

## Hardware assumptions

- iRobot Create3 (firmware H.2.6 or compatible)
- Raspberry Pi 4 (8 GB) on Ubuntu 22.04 + ROS2 Humble
- Slamtec RPLIDAR A1 on `/dev/RPLIDAR` (CH340 USB adapter)
- USB UVC webcam on `/dev/video0` supporting MJPG
- TurtleBot4 systemd service running on the RPi (provides Create3 bridge
  and the official Create3 robot_state_publisher)

## Documentation

- `docs/specs/2026-04-08-multi-machine-deployment-design.md` — design doc for the multi-machine architecture
- `docs/plans/2026-04-08-multi-machine-deployment.md` — implementation plan
- `docs/troubleshooting.md` — symptom → fix cookbook
- `docs/setup_new_robot.md` — full one-time commissioning checklist
- `CLAUDE.md` — context for AI assistants working in this repo

## License

MIT
