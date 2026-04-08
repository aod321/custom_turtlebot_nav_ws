# Multi-Machine Deployment — Design Doc

**Date:** 2026-04-08
**Status:** Approved
**Audience:** Robotics collaborators on the custom_turtlebot_nav_ws project

## Goal

Make the custom Create3 + RPi + Workstation system reproducibly handoff-able
to any collaborator. Specifically:

- Anyone can clone the repo, run a few standardized commands, and have a
  working dev environment connected to the live robot.
- The robot side (Create3 + RPi) must remain stable when workstation nodes
  join/leave; we do not want the DDS interference issues that have plagued
  the project so far.
- Heavy ML inference runs on the workstation, never on the RPi. RPi handles
  sensors + Nav2/AMCL only.
- All standard ROS2 tools (`rviz2`, `ros2 launch`, custom nodes) must keep
  working on the workstation.

## Constraints

- iRobot Create3 has limited compute and cannot tolerate many DDS endpoints
  on its `/tf`/`/odom` RELIABLE publishers without dropping messages.
- The RPi 4B has enough CPU for sensors + Nav2 but not for ML inference.
- The RPi has no GUI; RViz must run on the workstation.
- Only one collaborator works on the dedicated workstation at a time. Not
  multiple simultaneous workstations.
- Do not modify files under `/opt/ros/humble/`. The system turtlebot4
  service may be `apt upgrade`d at any time and our changes must survive.
- Workstations must be on the same WiFi/LAN as the RPi (5 GHz preferred).

## Topology

```
┌─────────────────────────┐         ┌──────────────────────────┐
│       Create3           │         │    Workstation           │
│    (192.168.186.2)      │         │    (Dell Precision 5680) │
│                         │         │                          │
│  motion_control         │         │  rviz2                   │
│  robot_state            │         │  custom_tb4_autonomy/    │
│  ...                    │         │    object_detector (ML)  │
│                         │         │  custom workstation_*    │
│  ROS_DOMAIN_ID=64       │         │    nodes                 │
│  Discovery client       │         │                          │
│  → 192.168.186.3:11811  │         │  ROS_DOMAIN_ID=64        │
└────────────┬────────────┘         │  Discovery super-client  │
             │ usb0                 │  → 192.168.111.230:11811 │
             │                      └──────────┬───────────────┘
             │                                 │ wlan0 (5 GHz)
             │                                 │
┌────────────┴─────────────────────────────────┴───────────────┐
│                  Raspberry Pi 4                              │
│                  (192.168.111.230 wlan0, 192.168.186.3 usb0) │
│                                                              │
│  turtlebot4.service (system service):                        │
│    ├─ turtlebot4_node (Create3 bridge)                        │
│    └─ robot_state_publisher (official Create3 base URDF)      │
│                                                              │
│  custom_tb4_bringup robot/full.launch.py (this project):     │
│    ├─ custom_extras_rsp (custom_tb4_description package)      │
│    │    URDF: rplidar_link, camera_link, pole_link            │
│    │    Coexists with system RSP, adds child frames of        │
│    │    base_link without conflict                            │
│    ├─ rplidar_composition (auto_standby=False)                │
│    ├─ v4l2_camera_node + image_transport plugins              │
│    ├─ slam_toolbox / amcl + nav2 (depending on launch)        │
│    └─ patrol_node (optional)                                  │
│                                                              │
│  fastdds_discovery_server.service (systemd):                 │
│    fastdds discovery -i 0 --listening-addresses 0.0.0.0:11811│
│                                                              │
│  ROS_DOMAIN_ID=64                                             │
│  ROS_DISCOVERY_SERVER=192.168.186.3:11811                     │
└──────────────────────────────────────────────────────────────┘
```

### Key topology decisions

| Decision | Why |
|---|---|
| `ROS_DOMAIN_ID=64` everywhere (incl. Create3) | Single global value, no per-machine override |
| Two robot_state_publishers coexist (system + `custom_extras_rsp`) | Don't modify system files; both publish disjoint child frames of base_link |
| FastDDS Discovery Server on RPi | Reduce DDS discovery storm; super-client mode hides workstation from Create3 |
| Server binds `0.0.0.0:11811` | Reachable from both usb0 (Create3) and wlan0 (workstation) |
| Workstation uses `ROS_SUPER_CLIENT=True` | Workstation does not participate in normal discovery — minimizes Create3 perturbation |

## Workspace structure

```
custom_turtlebot_nav_ws/
├── README.md                    # role-oriented onboarding
├── CONTRIBUTING.md              # commit/PR conventions
├── CLAUDE.md                    # AI agent context (project-local memory)
├── .gitignore
├── docs/
│   ├── specs/
│   │   └── 2026-04-08-multi-machine-deployment-design.md  (this file)
│   └── troubleshooting.md       # symptom → fix cookbook
├── scripts/
│   ├── setup_robot.sh           # source on RPi
│   ├── setup_workstation.sh     # source on workstation
│   ├── install_discovery_server.sh    # one-time RPi install
│   ├── fastdds_discovery_server.service
│   ├── check_network.sh         # diagnostics: WiFi band, ping, etc.
│   ├── smoke_test.sh            # workstation-side end-to-end check
│   └── verify_handoff.sh        # alias for smoke_test, for new collaborators
└── src/
    ├── custom_tb4_description/
    ├── custom_tb4_bringup/
    │   ├── launch/
    │   │   ├── robot/                # runs on RPi
    │   │   │   ├── sensors.launch.py
    │   │   │   ├── slam.launch.py
    │   │   │   ├── nav.launch.py
    │   │   │   └── full.launch.py
    │   │   └── workstation/          # runs on workstation
    │   │       ├── viz.launch.py     # rviz2 + (optional) foxglove_bridge
    │   │       ├── ml.launch.py      # object_detector
    │   │       └── full.launch.py    # viz + ml
    │   ├── config/
    │   │   ├── camera_calibration.yaml
    │   │   └── default.rviz          # minimal: TF + LaserScan + Map only
    │   └── ...
    └── custom_tb4_autonomy/
```

## DDS Discovery Server setup

### On the RPi — install systemd service

`scripts/fastdds_discovery_server.service`:
```ini
[Unit]
Description=FastDDS Discovery Server (custom_tb4)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
Environment=PATH=/opt/ros/humble/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ros/humble/bin/fastdds discovery -i 0 --listening-addresses 0.0.0.0:11811
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

`scripts/install_discovery_server.sh`:
```bash
#!/usr/bin/env bash
set -e
sudo cp scripts/fastdds_discovery_server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fastdds_discovery_server.service
sudo systemctl start fastdds_discovery_server.service
sudo systemctl status fastdds_discovery_server.service --no-pager
```

### On the RPi — `scripts/setup_robot.sh`

```bash
# Source AFTER /opt/ros/humble/setup.bash and the workspace install/setup.bash
export ROS_DOMAIN_ID=64
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER="192.168.186.3:11811"
unset FASTRTPS_DEFAULT_PROFILES_FILE   # no XML profile, use discovery server only
```

### Modifying `/etc/turtlebot4/setup.bash` (one-time, RPi)

The system turtlebot4 service uses this file to set its environment. We must
update it so the system nodes (turtlebot4_node, robot_state_publisher) also
join the discovery server.

Backup the original first:
```bash
sudo cp /etc/turtlebot4/setup.bash /etc/turtlebot4/setup.bash.bak
```

Edit it to set:
```bash
export ROS_DOMAIN_ID=64                              # was 0
export ROS_DISCOVERY_SERVER="192.168.186.3:11811"    # new
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp           # already set
unset FASTRTPS_DEFAULT_PROFILES_FILE                 # remove old XML profile
```

Then `sudo systemctl restart turtlebot4.service`. This is the one and only
exception to the "do not modify system files" rule, justified because the
system service is the only way to start `turtlebot4_node` reliably.

### On the workstation — `scripts/setup_workstation.sh`

```bash
# Source AFTER /opt/ros/humble/setup.bash and the workspace install/setup.bash
export ROS_DOMAIN_ID=64
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER="192.168.111.230:11811"
export ROS_SUPER_CLIENT=True
```

### On the Create3 — web config (`http://192.168.186.2`)

App Config page:
- ROS 2 Domain ID: **64**
- ROS 2 Namespace: (empty)
- RMW_IMPLEMENTATION: **rmw_fastrtps_cpp**
- Enable Fast DDS discovery server: ☑ **checked**
- Address and port: **`192.168.186.3:11811`**

Save → Restart application.

## Image bandwidth strategy

The camera topic is the only RPi → workstation stream large enough to stress
the WiFi link. 640×480×RGB at 30 FPS is ~28 MB/s = 220 Mbps.

### RPi side — publish raw + compressed

Install `ros-humble-image-transport-plugins` so v4l2_camera_node automatically
exposes JPEG-compressed transport.

Use the camera's native MJPG pixel format to skip RGB encoding entirely:
```python
parameters=[{
    'video_device': '/dev/video0',
    'pixel_format': 'MJPG',          # camera outputs JPEG directly
    'image_size': [640, 480],
    'camera_frame_id': 'camera_link',
    ...
}]
```

This saves significant CPU on the RPi.

### Workstation side — subscribe to compressed only

Default convention: workstation never subscribes to `/camera/image_raw`. Always
use `/camera/image_raw/compressed`. RViz, the ML object detector, and any
other consumer must follow this rule.

ROS2 DDS only sends data to matched subscribers, so as long as no workstation
subscriber for raw exists, no raw data crosses WiFi.

### Bandwidth budget

| Direction | Topic | Size |
|---|---|---|
| RPi → Workstation | `/camera/image_raw/compressed` (JPEG @ 15 fps) | ~16 Mbps |
| RPi → Workstation | `/scan` (1080 floats @ 10 Hz) | ~50 KB/s |
| RPi → Workstation | `/tf`, `/tf_static` | ~10 KB/s |
| RPi → Workstation | `/map` (one-shot, transient_local) | ~50 KB once |
| Workstation → RPi | `/detections` | <1 KB/s |
| Workstation → RPi | `/initialpose`, `/goal_pose` | event-based |

Total ≈ 16-17 Mbps. Trivially within 5 GHz WiFi capacity. On 2.4 GHz this is
borderline, hence the requirement to use 5 GHz when available.

### QoS conventions

| Topic | Publisher QoS (RPi) | Subscriber QoS (workstation) |
|---|---|---|
| `/scan` | RELIABLE / SENSOR_DATA | BEST_EFFORT |
| `/tf` | RELIABLE | RELIABLE (required) |
| `/tf_static` | RELIABLE / TRANSIENT_LOCAL | same |
| `/map` | RELIABLE / TRANSIENT_LOCAL | same |
| `/camera/image_raw/compressed` | RELIABLE | BEST_EFFORT |
| `/detections` | RELIABLE | RELIABLE |

## Documentation & onboarding

### README structure

The README is organized by **role**, not by feature. A new collaborator opens
the repo, sees a "who are you?" table, and follows the linked instructions.

```markdown
# custom_turtlebot_nav_ws

## System topology
[ASCII diagram]

## Who are you?
| Role          | On which machine | Purpose                                |
|---------------|------------------|----------------------------------------|
| Robot maintainer | RPi (SSH)     | Start sensors/Nav2/SLAM, edit URDF     |
| ML/algorithm | Workstation       | Run object_detector, tune ML models    |
| Mission/viz  | Workstation       | RViz, send goals, write high-level     |

## Quick start (by role)

### "I want to connect this robot from the workstation"
1. cd ~/code/custom_turtlebot_nav_ws
2. colcon build --symlink-install (if not built)
3. source install/setup.bash
4. source scripts/setup_workstation.sh
5. ros2 launch custom_tb4_bringup workstation/viz.launch.py
6. (optional) ros2 launch custom_tb4_bringup workstation/ml.launch.py

### "I want to (re)start sensors/Nav2 on the RPi"
1. ssh rpi
2. cd ~/custom_turtlebot_nav_ws
3. source install/setup.bash
4. source scripts/setup_robot.sh
5. ros2 launch custom_tb4_bringup robot/sensors.launch.py
   (or robot/slam.launch.py / robot/nav.launch.py / robot/full.launch.py)

## One-time setup (only when commissioning a new robot)
- Install fastdds_discovery_server.service on the RPi
- Edit /etc/turtlebot4/setup.bash on the RPi
- Configure Create3 web App Config
- See docs/setup_new_robot.md
```

### CLAUDE.md (AI agent context)

A markdown file at the project root with:
- Project goal and architecture summary
- All known gotchas (DDS, RPLIDAR auto_standby, AMCL TF cache, etc.)
- File paths to key configs
- Reminders: don't modify /opt/ros/humble, don't kill turtlebot4 service procs

This replaces the per-project entries currently in `~/.claude/projects/...`.

### `docs/troubleshooting.md`

Symptom → fix cookbook, integrating the existing `tb4_troubleshooting.md`
content. Indexed by symptom keyword for fast Ctrl-F lookup.

## Testing & verification

### Unit tests (already exist)

Pure-function tests in `custom_tb4_autonomy/test/`:
- `test_object_detector.py` (10 cases)
- `test_nav_goal_sender.py` (7 cases)
- `test_patrol.py` (12 cases)
- `test_launch_files.py`
- `test_config.py`

Run: `colcon test --packages-select custom_tb4_autonomy && colcon test-result --verbose`

New: `test_setup_scripts.py` — validate that sourcing `setup_robot.sh` /
`setup_workstation.sh` produces the expected env vars.

### `scripts/smoke_test.sh` — end-to-end check

Workstation-side script that verifies:
1. Discovery server reachable (`nc -zv 192.168.111.230 11811`)
2. Create3 nodes visible (`ros2 node list | grep motion_control`)
3. `/scan` has data (`ros2 topic hz /scan`)
4. `/tf` has data
5. `/camera/image_raw/compressed` has data (if RPi sensors launched)

This is run by every new collaborator on first connection. If smoke test
passes, handoff is successful.

### Failure cookbook (`docs/troubleshooting.md`)

Indexed by symptom:

| Symptom | First check | Then |
|---|---|---|
| `ros2 node list` empty / no Create3 | `systemctl status fastdds_discovery_server` | Restart turtlebot4.service |
| `/scan` no data | rplidar process on RPi? LIDAR powered? | USB reset CH340 |
| AMCL drops scan | TF time sync OK? | Restart AMCL |
| Nav2 ABORTED | Goal inside map? Costmap bounds? | Clear costmap |

## Out of scope

- Multiple simultaneous workstations (only one workstation supported)
- Remote (off-LAN) workstation access (foxglove bridge would be needed)
- ROS2 namespace prefixing (we use root namespace everywhere)
- ROS2 security (DDS-Security / SROS2)
- Continuous integration (deferred; will be added after the first stable release)

## Open questions / future work

- The Create3 web API uses ROS_DISCOVERY_SERVER but we have not verified
  the exact behavior when the server restarts. Need to test that Create3
  reconnects automatically vs requires its own restart.
- Migration plan for existing project memory in `~/.claude/projects/...`
  to project-local `CLAUDE.md` will be done as a follow-up commit.
