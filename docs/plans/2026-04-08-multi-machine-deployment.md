# Multi-Machine Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the custom_turtlebot_nav_ws to a multi-machine setup (RPi + dedicated workstation) using FastDDS Discovery Server, with all configuration living in the workspace (no `/opt/ros/humble/` modifications), and a role-oriented onboarding flow.

**Architecture:** RPi runs sensors + Nav2/SLAM + a FastDDS discovery server (systemd). Workstation runs RViz + ML inference as a DDS super-client. Create3 is also a discovery client. The git repo contains all setup scripts, launch files, and docs needed for any new collaborator to clone-and-go.

**Tech Stack:** ROS2 Humble, FastDDS, colcon, systemd, bash, NetworkManager.

**Spec:** `docs/specs/2026-04-08-multi-machine-deployment-design.md`

**Current State:**
- ✅ Workspace exists with 3 packages (description / bringup / autonomy), all build clean
- ✅ Sensors launch (`ros2 launch custom_tb4_bringup sensors.launch.py`) verified working on RPi
- ✅ System files in `/opt/ros/humble` are restored to official versions
- ❌ Launch files are flat in `launch/`, not split by robot/workstation
- ❌ No setup scripts, no discovery server, no smoke test, no role-oriented README
- ❌ Project-related memory still lives in `/home/yinzi/.claude/projects/...`

---

## Phase 1: Workspace skeleton (no behavior change yet)

### Task 1: Reorganize launch files into robot/ subdir

**Files:**
- Move: `src/custom_tb4_bringup/launch/sensors.launch.py` → `src/custom_tb4_bringup/launch/robot/sensors.launch.py`
- Move: `src/custom_tb4_bringup/launch/rplidar.launch.py` → `src/custom_tb4_bringup/launch/robot/rplidar.launch.py`
- Move: `src/custom_tb4_bringup/launch/camera.launch.py` → `src/custom_tb4_bringup/launch/robot/camera.launch.py`
- Move: `src/custom_tb4_bringup/launch/slam.launch.py` → `src/custom_tb4_bringup/launch/robot/slam.launch.py`
- Move: `src/custom_tb4_bringup/launch/nav.launch.py` → `src/custom_tb4_bringup/launch/robot/nav.launch.py`
- Move: `src/custom_tb4_bringup/launch/full_system.launch.py` → `src/custom_tb4_bringup/launch/robot/full.launch.py`
- Modify: `src/custom_tb4_bringup/CMakeLists.txt` (already installs `launch/` recursively, no change needed — verify)

- [ ] **Step 1: Move files**

```bash
cd ~/code/custom_turtlebot_nav_ws
mkdir -p src/custom_tb4_bringup/launch/robot
git mv src/custom_tb4_bringup/launch/sensors.launch.py src/custom_tb4_bringup/launch/robot/
git mv src/custom_tb4_bringup/launch/rplidar.launch.py src/custom_tb4_bringup/launch/robot/
git mv src/custom_tb4_bringup/launch/camera.launch.py src/custom_tb4_bringup/launch/robot/
git mv src/custom_tb4_bringup/launch/slam.launch.py src/custom_tb4_bringup/launch/robot/
git mv src/custom_tb4_bringup/launch/nav.launch.py src/custom_tb4_bringup/launch/robot/
git mv src/custom_tb4_bringup/launch/full_system.launch.py src/custom_tb4_bringup/launch/robot/full.launch.py
```

- [ ] **Step 2: Update sensors.launch.py path references inside slam.launch.py / nav.launch.py / full.launch.py**

The launches use `os.path.join(pkg_bringup, 'launch', 'sensors.launch.py')`. After move, change to `os.path.join(pkg_bringup, 'launch', 'robot', 'sensors.launch.py')`.

```bash
sed -i "s|'launch', 'sensors.launch.py'|'launch', 'robot', 'sensors.launch.py'|g" \
  src/custom_tb4_bringup/launch/robot/slam.launch.py \
  src/custom_tb4_bringup/launch/robot/nav.launch.py \
  src/custom_tb4_bringup/launch/robot/full.launch.py
```

Also `nav.launch.py` is included by `full.launch.py`:
```bash
sed -i "s|'launch', 'nav.launch.py'|'launch', 'robot', 'nav.launch.py'|g" \
  src/custom_tb4_bringup/launch/robot/full.launch.py
```

- [ ] **Step 3: Update CMakeLists.txt to install launch/ recursively**

Verify `src/custom_tb4_bringup/CMakeLists.txt` already does this:

```cmake
install(
  DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)
```

`DIRECTORY launch` already installs subdirectories recursively. No change needed.

- [ ] **Step 4: Build and verify launch file resolves**

```bash
cd ~/code/custom_turtlebot_nav_ws
colcon build --symlink-install --packages-select custom_tb4_bringup
source install/setup.bash
ros2 launch custom_tb4_bringup robot/sensors.launch.py --show-args 2>&1 | head -5
```
Expected: prints launch args without errors. (We're not running it, just verifying parse.)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(bringup): move launch files into robot/ subdir

Group launch files by where they run (robot vs workstation).
Updates internal references to sensors.launch.py path."
```

---

### Task 2: Create workstation/ launch dir with viz.launch.py

**Files:**
- Create: `src/custom_tb4_bringup/launch/workstation/viz.launch.py`
- Create: `src/custom_tb4_bringup/config/default.rviz`

- [ ] **Step 1: Create minimal default.rviz**

`src/custom_tb4_bringup/config/default.rviz`:
```yaml
Panels:
  - Class: rviz_common/Displays
    Name: Displays
  - Class: rviz_common/Views
    Name: Views
Visualization Manager:
  Class: ""
  Displays:
    - Class: rviz_default_plugins/TF
      Enabled: true
      Name: TF
      Show Arrows: false
      Show Axes: true
      Show Names: false
      Frame Timeout: 15
    - Class: rviz_default_plugins/LaserScan
      Enabled: true
      Name: LaserScan
      Topic:
        Value: /scan
        Reliability Policy: Best Effort
      Size (m): 0.03
      Color: 255; 0; 0
    - Class: rviz_default_plugins/Map
      Enabled: true
      Name: Map
      Topic:
        Value: /map
        Durability Policy: Transient Local
        Reliability Policy: Reliable
      Alpha: 0.7
  Global Options:
    Background Color: 48; 48; 48
    Fixed Frame: map
    Frame Rate: 30
  Views:
    Current:
      Class: rviz_default_plugins/Orbit
      Distance: 5.0
      Pitch: 1.0
      Yaw: 0
```

(Minimal: TF, LaserScan, Map only — no RobotModel/Image to avoid past segfaults.)

- [ ] **Step 2: Create viz.launch.py**

`src/custom_tb4_bringup/launch/workstation/viz.launch.py`:
```python
"""Workstation: launch RViz2 with the project default config.

Run on the workstation only. Requires:
  - workspace built and sourced
  - scripts/setup_workstation.sh sourced (sets DDS env vars)
  - RPi-side sensors already running (otherwise nothing to display)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_bringup = get_package_share_directory('custom_tb4_bringup')
    default_rviz = os.path.join(pkg_bringup, 'config', 'default.rviz')

    return LaunchDescription([
        DeclareLaunchArgument(
            'rviz_config',
            default_value=default_rviz,
            description='Path to RViz config file',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', LaunchConfiguration('rviz_config')],
            output='screen',
        ),
    ])
```

- [ ] **Step 3: Build and verify**

```bash
cd ~/code/custom_turtlebot_nav_ws
colcon build --symlink-install --packages-select custom_tb4_bringup
source install/setup.bash
ros2 launch custom_tb4_bringup workstation/viz.launch.py --show-args 2>&1 | head -10
```
Expected: prints `rviz_config` argument with default path.

- [ ] **Step 4: Commit**

```bash
git add src/custom_tb4_bringup/config/default.rviz src/custom_tb4_bringup/launch/workstation/viz.launch.py
git commit -m "feat(bringup): add workstation/viz.launch.py + minimal default.rviz

Minimal RViz config: TF, LaserScan, Map only.
Avoids RobotModel/Image displays that previously caused segfaults."
```

---

### Task 3: Create workstation/ml.launch.py and full.launch.py

**Files:**
- Create: `src/custom_tb4_bringup/launch/workstation/ml.launch.py`
- Create: `src/custom_tb4_bringup/launch/workstation/full.launch.py`

- [ ] **Step 1: Create ml.launch.py**

`src/custom_tb4_bringup/launch/workstation/ml.launch.py`:
```python
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
```

- [ ] **Step 2: Create workstation/full.launch.py**

`src/custom_tb4_bringup/launch/workstation/full.launch.py`:
```python
"""Workstation: launch RViz + ML object detector together."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    pkg_bringup = get_package_share_directory('custom_tb4_bringup')

    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_bringup, 'launch', 'workstation', 'viz.launch.py'))),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_bringup, 'launch', 'workstation', 'ml.launch.py'))),
    ])
```

- [ ] **Step 3: Build and verify**

```bash
cd ~/code/custom_turtlebot_nav_ws
colcon build --symlink-install --packages-select custom_tb4_bringup
source install/setup.bash
ros2 launch custom_tb4_bringup workstation/ml.launch.py --show-args
ros2 launch custom_tb4_bringup workstation/full.launch.py --show-args
```
Expected: both print args without errors.

- [ ] **Step 4: Commit**

```bash
git add src/custom_tb4_bringup/launch/workstation/
git commit -m "feat(bringup): add workstation/ml.launch.py and full.launch.py

ml.launch.py runs object_detector.
full.launch.py runs viz + ml together."
```

---

### Task 4: Switch camera launch to MJPG pixel format

**Files:**
- Modify: `src/custom_tb4_bringup/launch/robot/camera.launch.py`
- Modify: `src/custom_tb4_bringup/package.xml`

- [ ] **Step 1: Add image_transport_plugins exec_depend in package.xml**

Edit `src/custom_tb4_bringup/package.xml`. After the existing `<exec_depend>v4l2_camera</exec_depend>` line, add:

```xml
  <exec_depend>image_transport_plugins</exec_depend>
```

- [ ] **Step 2: Update camera.launch.py to use MJPG**

Edit `src/custom_tb4_bringup/launch/robot/camera.launch.py`. Find the parameters dict and add `pixel_format`:

Current parameters:
```python
parameters=[{
    'video_device': LaunchConfiguration('video_device'),
    'image_size': [640, 480],
    'camera_frame_id': 'camera_link',
    'camera_info_url': LaunchConfiguration('camera_info_url'),
}],
```

Replace with:
```python
parameters=[{
    'video_device': LaunchConfiguration('video_device'),
    'pixel_format': 'MJPG',
    'image_size': [640, 480],
    'camera_frame_id': 'camera_link',
    'camera_info_url': LaunchConfiguration('camera_info_url'),
}],
```

- [ ] **Step 3: Install image_transport_plugins on RPi**

```bash
ssh rpi 'echo turtlebot4 | sudo -S apt-get install -y ros-humble-image-transport-plugins'
```
Expected: package installed (or "already newest version").

- [ ] **Step 4: Build and verify launch file parses**

```bash
cd ~/code/custom_turtlebot_nav_ws
colcon build --symlink-install --packages-select custom_tb4_bringup
source install/setup.bash
ros2 launch custom_tb4_bringup robot/camera.launch.py --show-args
```
Expected: parses without errors.

- [ ] **Step 5: Commit**

```bash
git add src/custom_tb4_bringup/package.xml src/custom_tb4_bringup/launch/robot/camera.launch.py
git commit -m "feat(bringup): use MJPG pixel format + image_transport_plugins

Camera outputs JPEG natively, saving CPU on RPi.
Adds image_transport_plugins dep for compressed transport."
```

---

## Phase 2: Setup scripts (DDS Discovery Server)

### Task 5: Create scripts/setup_robot.sh

**Files:**
- Create: `scripts/setup_robot.sh`

- [ ] **Step 1: Create the script**

`scripts/setup_robot.sh`:
```bash
#!/usr/bin/env bash
# Source on the RPi after sourcing /opt/ros/humble/setup.bash and the
# workspace install/setup.bash.
#
# Sets DDS environment for the multi-machine architecture: domain 64,
# FastDDS Discovery Server bound to RPi's usb0 IP (so Create3 can also
# reach it via USB-Ethernet).

export ROS_DOMAIN_ID=64
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER="192.168.186.3:11811"

# Remove any inherited XML profile from earlier turtlebot4 setup; we now
# use the discovery server protocol exclusively.
unset FASTRTPS_DEFAULT_PROFILES_FILE

echo "[setup_robot] ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo "[setup_robot] ROS_DISCOVERY_SERVER=$ROS_DISCOVERY_SERVER"
echo "[setup_robot] RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/setup_robot.sh
```

- [ ] **Step 3: Test it produces the expected env**

```bash
bash -c 'source scripts/setup_robot.sh && env | grep -E "ROS_DOMAIN_ID|ROS_DISCOVERY_SERVER|RMW_IMPLEMENTATION"'
```
Expected:
```
ROS_DOMAIN_ID=64
RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ROS_DISCOVERY_SERVER=192.168.186.3:11811
```

- [ ] **Step 4: Commit**

```bash
git add scripts/setup_robot.sh
git commit -m "feat(scripts): add setup_robot.sh for RPi DDS env"
```

---

### Task 6: Create scripts/setup_workstation.sh

**Files:**
- Create: `scripts/setup_workstation.sh`

- [ ] **Step 1: Create the script**

`scripts/setup_workstation.sh`:
```bash
#!/usr/bin/env bash
# Source on the workstation after sourcing /opt/ros/humble/setup.bash and
# the workspace install/setup.bash.
#
# Configures the workstation as a FastDDS Discovery Server SUPER-CLIENT.
# Super-client mode: this node only learns about endpoints from the
# discovery server on the RPi; it does NOT broadcast its own discovery
# messages on the LAN. This minimizes perturbation of Create3's DDS state.

export ROS_DOMAIN_ID=64
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER="192.168.111.230:11811"
export ROS_SUPER_CLIENT=True

unset FASTRTPS_DEFAULT_PROFILES_FILE

echo "[setup_workstation] ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo "[setup_workstation] ROS_DISCOVERY_SERVER=$ROS_DISCOVERY_SERVER"
echo "[setup_workstation] ROS_SUPER_CLIENT=$ROS_SUPER_CLIENT"
echo "[setup_workstation] RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
```

- [ ] **Step 2: Make executable + test**

```bash
chmod +x scripts/setup_workstation.sh
bash -c 'source scripts/setup_workstation.sh && env | grep -E "ROS_DOMAIN_ID|ROS_DISCOVERY_SERVER|ROS_SUPER_CLIENT"'
```
Expected:
```
ROS_DOMAIN_ID=64
ROS_DISCOVERY_SERVER=192.168.111.230:11811
ROS_SUPER_CLIENT=True
```

- [ ] **Step 3: Commit**

```bash
git add scripts/setup_workstation.sh
git commit -m "feat(scripts): add setup_workstation.sh (DDS super-client)"
```

---

### Task 7: Create discovery server systemd service files

**Files:**
- Create: `scripts/fastdds_discovery_server.service`
- Create: `scripts/install_discovery_server.sh`

- [ ] **Step 1: Create the service unit**

`scripts/fastdds_discovery_server.service`:
```ini
[Unit]
Description=FastDDS Discovery Server (custom_turtlebot_nav_ws)
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

- [ ] **Step 2: Create the install helper**

`scripts/install_discovery_server.sh`:
```bash
#!/usr/bin/env bash
# Run ON THE RPi (one time). Installs and starts the FastDDS discovery
# server as a systemd service so it survives reboots.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/fastdds_discovery_server.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "ERROR: $SERVICE_FILE not found"
    exit 1
fi

echo "Installing fastdds_discovery_server.service..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fastdds_discovery_server.service
sudo systemctl restart fastdds_discovery_server.service
sleep 2
sudo systemctl status fastdds_discovery_server.service --no-pager
```

- [ ] **Step 3: Make install script executable**

```bash
chmod +x scripts/install_discovery_server.sh
```

- [ ] **Step 4: Verify the unit file is valid (parse-only)**

```bash
systemd-analyze verify scripts/fastdds_discovery_server.service 2>&1 || true
```
Expected: no parse errors. (May print warnings about user existence on this machine, ignore.)

- [ ] **Step 5: Commit**

```bash
git add scripts/fastdds_discovery_server.service scripts/install_discovery_server.sh
git commit -m "feat(scripts): add FastDDS discovery server systemd unit"
```

---

### Task 8: Create scripts/check_network.sh

**Files:**
- Create: `scripts/check_network.sh`

- [ ] **Step 1: Create the script**

`scripts/check_network.sh`:
```bash
#!/usr/bin/env bash
# Quick network sanity check for the custom_tb4 multi-machine setup.
# Run on either the RPi or the workstation. Reports WiFi band, signal,
# RPi reachability, and discovery server reachability.

set -u

RPI_IP="192.168.111.230"
DISC_PORT=11811

echo "=== WiFi connection ==="
if command -v nmcli >/dev/null 2>&1; then
    nmcli -f IN-USE,SSID,CHAN,RATE,SIGNAL device wifi list 2>/dev/null | head -5
elif command -v iwgetid >/dev/null 2>&1; then
    iwgetid -r
else
    echo "(no nmcli or iwgetid; skipping)"
fi

echo
echo "=== Active wireless link ==="
if command -v iw >/dev/null 2>&1; then
    for iface in $(ls /sys/class/net | grep -E '^(wl|wlan)'); do
        echo "[$iface]"
        iw dev "$iface" link 2>/dev/null | grep -E 'SSID|freq|signal|tx bitrate'
    done
fi

echo
echo "=== Ping RPi ($RPI_IP) ==="
if ping -c 3 -W 1 "$RPI_IP" >/dev/null 2>&1; then
    rtt=$(ping -c 3 -W 1 "$RPI_IP" | tail -1)
    echo "OK: $rtt"
else
    echo "FAIL: cannot reach $RPI_IP"
fi

echo
echo "=== Discovery server port ($RPI_IP:$DISC_PORT) ==="
if command -v nc >/dev/null 2>&1; then
    if nc -zvw 2 "$RPI_IP" "$DISC_PORT" 2>&1; then
        echo "OK: port reachable"
    else
        echo "FAIL: discovery server not reachable"
    fi
else
    echo "(nc not installed; skipping)"
fi

echo
echo "=== ROS env ==="
echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-(unset)}"
echo "ROS_DISCOVERY_SERVER=${ROS_DISCOVERY_SERVER:-(unset)}"
echo "ROS_SUPER_CLIENT=${ROS_SUPER_CLIENT:-(unset)}"
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-(unset)}"
```

- [ ] **Step 2: Make executable + test on workstation**

```bash
chmod +x scripts/check_network.sh
./scripts/check_network.sh
```
Expected: prints WiFi info, ping result, port check. Some sections may print "not installed" or "FAIL" — that's diagnostic info, not an error.

- [ ] **Step 3: Commit**

```bash
git add scripts/check_network.sh
git commit -m "feat(scripts): add check_network.sh diagnostic"
```

---

### Task 9: Create scripts/smoke_test.sh

**Files:**
- Create: `scripts/smoke_test.sh`

- [ ] **Step 1: Create the script**

`scripts/smoke_test.sh`:
```bash
#!/usr/bin/env bash
# End-to-end handoff verification. Run ON THE WORKSTATION after sourcing
# setup_workstation.sh. Returns 0 if everything passes, non-zero on first
# failure.
set -u

PASS=0
FAIL=0

ok()   { echo "  [OK]   $*"; PASS=$((PASS+1)); }
warn() { echo "  [WARN] $*"; }
bad()  { echo "  [FAIL] $*"; FAIL=$((FAIL+1)); }

echo "=== 1. Environment ==="
[ "${ROS_DOMAIN_ID:-}" = "64" ] && ok "ROS_DOMAIN_ID=64" || bad "ROS_DOMAIN_ID is '${ROS_DOMAIN_ID:-(unset)}', expected 64"
[ -n "${ROS_DISCOVERY_SERVER:-}" ] && ok "ROS_DISCOVERY_SERVER set: $ROS_DISCOVERY_SERVER" || bad "ROS_DISCOVERY_SERVER not set"
[ "${ROS_SUPER_CLIENT:-}" = "True" ] && ok "ROS_SUPER_CLIENT=True" || warn "ROS_SUPER_CLIENT is '${ROS_SUPER_CLIENT:-(unset)}', expected True"

echo
echo "=== 2. Discovery server reachable ==="
if nc -zvw 2 192.168.111.230 11811 >/dev/null 2>&1; then
    ok "discovery server port open"
else
    bad "discovery server unreachable at 192.168.111.230:11811"
    echo "  → On RPi run: sudo systemctl status fastdds_discovery_server"
fi

echo
echo "=== 3. ROS2 nodes visible ==="
ros2 daemon stop >/dev/null 2>&1 || true
ros2 daemon start >/dev/null 2>&1 || true
sleep 2

NODES=$(ros2 node list 2>/dev/null)
echo "$NODES" | grep -q motion_control && ok "Create3 motion_control visible" || bad "Create3 motion_control NOT visible"
echo "$NODES" | grep -q robot_state && ok "Create3 robot_state visible" || warn "Create3 robot_state NOT visible"

echo
echo "=== 4. Topics with data ==="
check_hz() {
    local topic="$1"
    if timeout 5 ros2 topic hz "$topic" 2>&1 | grep -q "average rate"; then
        ok "$topic streaming"
    else
        bad "$topic NOT streaming"
    fi
}
check_hz /tf
check_hz /scan

if timeout 3 ros2 topic hz /camera/image_raw/compressed 2>&1 | grep -q "average rate"; then
    ok "/camera/image_raw/compressed streaming"
else
    warn "/camera/image_raw/compressed NOT streaming (run robot/sensors.launch.py on RPi?)"
fi

echo
echo "=== Summary ==="
echo "  passed: $PASS"
echo "  failed: $FAIL"
[ "$FAIL" -eq 0 ] && { echo "SMOKE TEST PASSED"; exit 0; } || { echo "SMOKE TEST FAILED"; exit 1; }
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/smoke_test.sh
```

- [ ] **Step 3: Commit (don't run yet — RPi side not set up)**

```bash
git add scripts/smoke_test.sh
git commit -m "feat(scripts): add smoke_test.sh handoff verification"
```

---

## Phase 3: Documentation

### Task 10: Rewrite README.md role-oriented

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README content**

Open `README.md` and replace its full content with:

```markdown
# custom_turtlebot_nav_ws

ROS2 Humble workspace for a bare iRobot Create3 + RPLIDAR A1 + USB camera,
deployed across a Raspberry Pi 4 (robot side) and a dedicated workstation
(ML inference + visualization).

## System topology

```
Create3 (192.168.186.2)            Workstation (5GHz WiFi)
   │                                  │
   │ usb0                             │ wlan0
   │                                  │
   └─────── RPi 4 (192.168.111.230) ──┘
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
ros2 launch custom_tb4_bringup workstation/viz.launch.py
ros2 launch custom_tb4_bringup workstation/ml.launch.py     # in another terminal
```

### "I want to (re)start sensors / SLAM / Nav2 on the RPi"

```bash
ssh rpi
cd ~/custom_turtlebot_nav_ws
source install/setup.bash
source scripts/setup_robot.sh

# Pick one mode:
ros2 launch custom_tb4_bringup robot/sensors.launch.py    # sensors only
ros2 launch custom_tb4_bringup robot/slam.launch.py       # sensors + SLAM
ros2 launch custom_tb4_bringup robot/nav.launch.py \
     map:=/home/ubuntu/maps/my_environment.yaml           # sensors + AMCL + Nav2
ros2 launch custom_tb4_bringup robot/full.launch.py \
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
| `custom_tb4_bringup` | Launch files (split by `robot/` and `workstation/`) and shared config (camera calibration, default RViz). |
| `custom_tb4_autonomy` | Python nodes: `object_detector`, `patrol`, `nav_goal_sender`, `tf_broadcaster`, `teleop`. |

## One-time commissioning (only when setting up a new robot)

See `docs/setup_new_robot.md` for the full checklist. Summary:

1. Install ROS2 Humble + `image-transport-plugins` on the RPi.
2. Install the FastDDS discovery server systemd service:
   ```bash
   ssh rpi
   cd ~/custom_turtlebot_nav_ws
   ./scripts/install_discovery_server.sh
   ```
3. Edit `/etc/turtlebot4/setup.bash` on the RPi to set `ROS_DOMAIN_ID=64`,
   `ROS_DISCOVERY_SERVER=192.168.186.3:11811`, and unset
   `FASTRTPS_DEFAULT_PROFILES_FILE`. Restart `turtlebot4.service`.
4. In the Create3 web UI (`http://192.168.186.2`, App Config), set:
   - ROS 2 Domain ID: 64
   - Enable Fast DDS discovery server: ☑
   - Address and port: `192.168.186.3:11811`
   - Save and restart application.

## Hardware assumptions

- iRobot Create3 (firmware H.2.6 or compatible)
- Raspberry Pi 4 (8 GB) on Ubuntu 22.04 + ROS2 Humble
- Slamtec RPLIDAR A1 on `/dev/RPLIDAR` (CH340 USB adapter)
- USB UVC webcam on `/dev/video0` supporting MJPG
- TurtleBot4 systemd service running on the RPi (provides Create3 bridge
  and the official Create3 robot_state_publisher)

## Documentation

- `docs/specs/2026-04-08-multi-machine-deployment-design.md` — design doc for the multi-machine architecture
- `docs/troubleshooting.md` — symptom → fix cookbook (DDS, AMCL, costmap, etc.)
- `docs/setup_new_robot.md` — full one-time commissioning checklist
- `CLAUDE.md` — context for AI assistants working in this repo

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README role-oriented for multi-machine setup"
```

---

### Task 11: Create CLAUDE.md (project-local memory)

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Write CLAUDE.md**

`CLAUDE.md`:
```markdown
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
| `ros2 topic echo` fails but Python rclpy subscriber works | ros2 daemon cache stale | `ros2 daemon stop && ros2 daemon start` |
| RPLIDAR `/scan` Publisher count = 0 | Stock turtlebot4 launch sets `auto_standby: True` | Our `robot/rplidar.launch.py` forces `False` |
| AMCL drops every scan with "timestamp earlier than transform cache" | static_transform_publisher restarted with newer timestamp than scans | Don't restart static TF publishers; if you must, also restart AMCL |
| Nav2 ABORTED with `worldToMap failed` | Robot is outside map bounds (often because dock is at map edge) | Build a larger map with more padding around the dock |
| RViz crashes on startup with auto-loaded config | RViz Image / RobotModel display interaction with NVIDIA driver | Use minimal `default.rviz` (TF + LaserScan + Map only); add other displays manually |
| RPi's `source /opt/ros/humble/setup.bash` works in bash but not zsh | zsh doesn't expand `BASH_SOURCE` the same way | Use `source /opt/ros/humble/setup.zsh` or wrap in `bash -c '...'` |

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

- If it runs on the RPi: put it under `src/custom_tb4_bringup/launch/robot/`
- If it runs on the workstation: put it under `src/custom_tb4_bringup/launch/workstation/`
- Document the assumed prerequisites (sensors running? sourced setup script?) in the docstring.

## How to debug

Use ROS2 CLI tools first, not ad-hoc Python:
- `ros2 node list` / `ros2 node info <node>`
- `ros2 topic list` / `ros2 topic info <topic> --verbose` / `ros2 topic hz <topic>`
- `ros2 run tf2_ros tf2_echo <parent> <child>`
- `scripts/check_network.sh` for network diagnostics
- `scripts/smoke_test.sh` for end-to-end handoff verification
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md project-local agent context"
```

---

### Task 12: Create docs/troubleshooting.md

**Files:**
- Create: `docs/troubleshooting.md`

- [ ] **Step 1: Pull existing notes from /home/yinzi/tb4_troubleshooting.md and adapt**

Read `/home/yinzi/tb4_troubleshooting.md`. Reuse its content but reformat
for the new workspace structure. Key changes:
- Reference the new `scripts/` and `launch/robot/`, `launch/workstation/` paths
- Drop references to `tb4_autonomy_ws` (deprecated) and `/opt/ros/humble/` mods (no longer needed)
- Add the discovery server troubleshooting section

`docs/troubleshooting.md`:
```markdown
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
   ros2 launch custom_tb4_bringup robot/sensors.launch.py
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
ros2 launch custom_tb4_bringup robot/nav.launch.py map:=/home/ubuntu/maps/my_environment.yaml
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
```

- [ ] **Step 2: Commit**

```bash
git add docs/troubleshooting.md
git commit -m "docs: add troubleshooting cookbook"
```

---

### Task 13: Create docs/setup_new_robot.md

**Files:**
- Create: `docs/setup_new_robot.md`

- [ ] **Step 1: Write the file**

`docs/setup_new_robot.md`:
```markdown
# Setting up a new robot (one-time commissioning)

This is the full checklist for bringing up a brand-new RPi + Create3 +
custom_tb4 sensor stack from scratch. Once done, day-to-day operations
follow the role-oriented Quick Start in `README.md`.

## 1. RPi: install ROS2 Humble and the TurtleBot4 system service

Follow the official iRobot/Clearpath guide. After this step you should
have:
- `/opt/ros/humble/` populated
- `turtlebot4.service` running
- `usb0` interface up at `192.168.186.3`, Create3 reachable at `192.168.186.2`

## 2. RPi: install image_transport_plugins

```bash
ssh rpi
sudo apt-get install -y ros-humble-image-transport-plugins
```

## 3. RPi: install the FastDDS discovery server systemd unit

```bash
ssh rpi
git clone https://github.com/<your_user>/custom_turtlebot_nav_ws.git ~/custom_turtlebot_nav_ws
cd ~/custom_turtlebot_nav_ws
./scripts/install_discovery_server.sh
```

Verify it's running and listening:
```bash
sudo systemctl status fastdds_discovery_server
sudo ss -tlnp | grep 11811
```

## 4. RPi: edit `/etc/turtlebot4/setup.bash`

Back up the original, then change these lines:

```bash
sudo cp /etc/turtlebot4/setup.bash /etc/turtlebot4/setup.bash.bak
sudo nano /etc/turtlebot4/setup.bash
```

Set:
```bash
export ROS_DOMAIN_ID=64
export ROS_DISCOVERY_SERVER="192.168.186.3:11811"
export RMW_IMPLEMENTATION="rmw_fastrtps_cpp"
unset FASTRTPS_DEFAULT_PROFILES_FILE
```

Restart the service so it picks up the new env:
```bash
sudo systemctl restart turtlebot4.service
```

## 5. Create3: web App Config

Open `http://192.168.186.2` from a workstation that can route to the usb0
network (or via SSH port forward from the RPi). Go to **App Config** and set:

| Field | Value |
|---|---|
| ROS 2 Domain ID | 64 |
| ROS 2 Namespace | (leave empty) |
| RMW_IMPLEMENTATION | rmw_fastrtps_cpp |
| Enable Fast DDS discovery server? | ☑ checked |
| Address and port of Fast DDS discovery server | `192.168.186.3:11811` |

Save → click **Restart application**. Wait ~2 minutes for Create3 to come
back. Verify with:
```bash
ssh rpi 'source /opt/ros/humble/setup.bash && source ~/custom_turtlebot_nav_ws/install/setup.bash && source ~/custom_turtlebot_nav_ws/scripts/setup_robot.sh && ros2 node list | grep motion_control'
```

## 6. RPi: build the workspace

```bash
ssh rpi
cd ~/custom_turtlebot_nav_ws
colcon build --symlink-install
source install/setup.bash
source scripts/setup_robot.sh
```

## 7. Workstation: clone, build, smoke test

```bash
git clone https://github.com/<your_user>/custom_turtlebot_nav_ws.git ~/code/custom_turtlebot_nav_ws
cd ~/code/custom_turtlebot_nav_ws
colcon build --symlink-install
source install/setup.bash
source scripts/setup_workstation.sh

./scripts/smoke_test.sh
```

If smoke test passes, commissioning is complete. Proceed to the role-oriented
Quick Start in `README.md`.

## 8. Optional: udev rule for stable RPLIDAR device path

If `/dev/RPLIDAR` is not already a symlink to the CH340 adapter, install
the udev rule:

```bash
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="RPLIDAR", MODE="0666"' | sudo tee /etc/udev/rules.d/99-rplidar.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/setup_new_robot.md
git commit -m "docs: add setup_new_robot.md commissioning checklist"
```

---

## Phase 4: Memory migration

### Task 14: Migrate /home/yinzi memory to project

**Files:**
- Read: `/home/yinzi/.claude/projects/-home-yinzi/memory/MEMORY.md`
- Read: `/home/yinzi/.claude/projects/-home-yinzi/memory/feedback_*.md`
- Read: `/home/yinzi/.claude/projects/-home-yinzi/memory/project_*.md`
- Read: `/home/yinzi/.claude/projects/-home-yinzi/memory/reference_*.md`
- Modify: `CLAUDE.md` (already created in Task 11; integrate any unique content)
- Delete (after migration): project-specific memory files in `~/.claude/projects/...`
- Move: `/home/yinzi/tb4_troubleshooting.md` → already absorbed into `docs/troubleshooting.md` in Task 12

- [ ] **Step 1: Read each existing memory file and identify project-specific content**

```bash
ls -la /home/yinzi/.claude/projects/-home-yinzi/memory/
cat /home/yinzi/.claude/projects/-home-yinzi/memory/MEMORY.md
for f in /home/yinzi/.claude/projects/-home-yinzi/memory/{feedback,project,reference}_*.md; do
  echo "=== $f ==="
  cat "$f"
done
```

Categorize each file:
- **Project-specific** (RPi connection, dock position, RViz config, ROS2 daemon, handoff principle): merge into `CLAUDE.md`
- **Cross-project** (user's workstation hardware, zsh, conda issues): leave in `~/.claude/projects/...`

- [ ] **Step 2: For each project-specific entry, verify it's already covered in CLAUDE.md**

The CLAUDE.md created in Task 11 already covers:
- DDS subscriber issue (gotcha table)
- ros2 daemon cache (gotcha table)
- RPLIDAR auto_standby (gotcha table)
- AMCL TF cache issue (gotcha table)
- Nav2 worldToMap failure (gotcha table)
- RViz auto-config crash (gotcha table)
- zsh / conda Python conflict (gotcha table)
- SSH connection (`ssh rpi`)
- Charging dock position
- Don't kill turtlebot4.service
- Don't modify /opt/ros/humble (Hard rules)

If anything is missing, append it to `CLAUDE.md` now.

- [ ] **Step 3: Delete the migrated entries from `~/.claude/projects/...`**

```bash
rm /home/yinzi/.claude/projects/-home-yinzi/memory/feedback_rviz_config.md
rm /home/yinzi/.claude/projects/-home-yinzi/memory/feedback_ros2_daemon.md
rm /home/yinzi/.claude/projects/-home-yinzi/memory/project_dock_position.md
rm /home/yinzi/.claude/projects/-home-yinzi/memory/reference_rpi.md
```

Keep these (cross-project, not robot-specific):
- `feedback_handoff_principle.md`
- `user_setup.md`

Update `MEMORY.md` to remove the deleted entries:

```bash
cat > /home/yinzi/.claude/projects/-home-yinzi/memory/MEMORY.md << 'EOF'
- [User setup](user_setup.md) — Dell Precision 5680, zsh shell, Intel+NVIDIA GPU, ROS2 Humble
- [Handoff principle](feedback_handoff_principle.md) — All ROS2 work must be reproducible via standard colcon/ros2 launch flow, no AI/SSH lock-in
EOF
```

- [ ] **Step 4: Move /home/yinzi/tb4_troubleshooting.md (already absorbed)**

```bash
# Already absorbed into docs/troubleshooting.md in Task 12, just delete the old copy
rm -f /home/yinzi/tb4_troubleshooting.md
```

- [ ] **Step 5: Commit (CLAUDE.md may already be committed; only commit if amended)**

```bash
cd ~/code/custom_turtlebot_nav_ws
git status   # check if CLAUDE.md was modified
# If yes:
git add CLAUDE.md
git commit -m "docs(claude): integrate migrated project memory entries"
```

---

## Phase 5: RPi-side deployment

### Task 15: Deploy the new workspace to the RPi

**Files (on RPi):**
- Replace: `~/custom_turtlebot_nav_ws/` (existing skeleton)

- [ ] **Step 1: Push local repo to GitHub first**

```bash
cd ~/code/custom_turtlebot_nav_ws
git push origin main
```
Expected: push succeeds.

- [ ] **Step 2: On the RPi, fetch the new code**

```bash
ssh rpi
cd ~/custom_turtlebot_nav_ws
# If this is a git checkout:
git fetch origin && git reset --hard origin/main
# If it's NOT a git checkout, replace it:
# cd ~ && rm -rf custom_turtlebot_nav_ws && git clone https://github.com/aod321/custom_turtlebot_nav_ws.git
```

- [ ] **Step 3: Build on the RPi**

```bash
cd ~/custom_turtlebot_nav_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 pkg list | grep custom_tb4
```
Expected: `custom_tb4_autonomy`, `custom_tb4_bringup`, `custom_tb4_description` all listed.

- [ ] **Step 4: Verify launch files installed**

```bash
ls install/custom_tb4_bringup/share/custom_tb4_bringup/launch/robot/
ls install/custom_tb4_bringup/share/custom_tb4_bringup/launch/workstation/
```
Expected: both directories exist with `*.launch.py` files.

---

### Task 16: Install the discovery server on the RPi

- [ ] **Step 1: Run the install script**

```bash
ssh rpi
cd ~/custom_turtlebot_nav_ws
./scripts/install_discovery_server.sh
```
Expected: prints `Active: active (running)` for the systemd unit.

- [ ] **Step 2: Verify the server is listening**

```bash
ssh rpi 'sudo ss -tlnp | grep 11811'
```
Expected: a line showing `0.0.0.0:11811` listening.

- [ ] **Step 3: Verify reachability from the workstation**

```bash
nc -zvw 2 192.168.111.230 11811
```
Expected: `succeeded`.

---

### Task 17: Update `/etc/turtlebot4/setup.bash`

- [ ] **Step 1: Back up and edit**

```bash
ssh rpi
sudo cp /etc/turtlebot4/setup.bash /etc/turtlebot4/setup.bash.bak
```

Read the current contents and add/replace these lines:
```bash
export ROS_DOMAIN_ID=64
export ROS_DISCOVERY_SERVER="192.168.186.3:11811"
export RMW_IMPLEMENTATION="rmw_fastrtps_cpp"
unset FASTRTPS_DEFAULT_PROFILES_FILE
```

Use `sudo nano /etc/turtlebot4/setup.bash` or:
```bash
ssh rpi 'sudo sed -i \
  -e "s|^export ROS_DOMAIN_ID=.*|export ROS_DOMAIN_ID=64|" \
  -e "/^export FASTRTPS_DEFAULT_PROFILES_FILE/d" \
  /etc/turtlebot4/setup.bash'

ssh rpi 'grep -q ROS_DISCOVERY_SERVER /etc/turtlebot4/setup.bash || \
  echo "turtlebot4" | sudo -S tee -a /etc/turtlebot4/setup.bash <<EOF
export ROS_DISCOVERY_SERVER="192.168.186.3:11811"
EOF'
```

- [ ] **Step 2: Restart the turtlebot4 service**

```bash
ssh rpi 'echo turtlebot4 | sudo -S systemctl restart turtlebot4.service'
sleep 20
```

- [ ] **Step 3: Verify Create3 nodes come back**

```bash
ssh rpi 'source /opt/ros/humble/setup.bash && source ~/custom_turtlebot_nav_ws/install/setup.bash && source ~/custom_turtlebot_nav_ws/scripts/setup_robot.sh && ros2 daemon stop && ros2 daemon start && ros2 node list 2>&1 | grep -E "motion_control|robot_state|rplidar"'
```
Expected: at least `motion_control` and `robot_state` (rplidar may not show until launched).

---

### Task 18: Update Create3 web App Config (manual user step)

- [ ] **Step 1: Wait for user to manually update Create3 config**

This step requires the user to:
1. Open `http://192.168.186.2` (e.g., from the RPi via `firefox` or via SSH port-forward)
2. Go to **App Config**
3. Verify/set:
   - ROS 2 Domain ID: 64
   - Enable Fast DDS discovery server: ☑ checked
   - Address and port: `192.168.186.3:11811`
4. Save → Restart application
5. Wait 2 minutes for Create3 to fully come back

Pause and ask the user to confirm before continuing.

- [ ] **Step 2: Verify Create3 is reachable through the discovery server**

```bash
ssh rpi 'source /opt/ros/humble/setup.bash && source ~/custom_turtlebot_nav_ws/install/setup.bash && source ~/custom_turtlebot_nav_ws/scripts/setup_robot.sh && ros2 daemon stop && ros2 daemon start && sleep 2 && ros2 node list | grep motion_control'
```
Expected: `motion_control` present.

---

## Phase 6: Workstation verification

### Task 19: Run smoke test from workstation

- [ ] **Step 1: Source env on workstation**

```bash
cd ~/code/custom_turtlebot_nav_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
source scripts/setup_workstation.sh
```

- [ ] **Step 2: Run smoke test**

```bash
./scripts/smoke_test.sh
```
Expected: `SMOKE TEST PASSED` (camera may show as WARN if RPi sensors aren't launched yet — that's fine).

- [ ] **Step 3: If failures, troubleshoot per docs/troubleshooting.md**

Stop, fix, and re-run before continuing.

---

### Task 20: End-to-end RViz visualization test

- [ ] **Step 1: Start RPi sensors**

```bash
ssh rpi
cd ~/custom_turtlebot_nav_ws
source install/setup.bash
source scripts/setup_robot.sh
ros2 launch custom_tb4_bringup robot/sensors.launch.py
# Leave running. Open another terminal to continue.
```

- [ ] **Step 2: Re-run smoke test from workstation, expect camera now also OK**

```bash
./scripts/smoke_test.sh
```
Expected: all PASS, no WARN.

- [ ] **Step 3: Launch RViz on workstation**

```bash
cd ~/code/custom_turtlebot_nav_ws
source install/setup.bash
source scripts/setup_workstation.sh
ros2 launch custom_tb4_bringup workstation/viz.launch.py
```

In RViz: confirm the LaserScan and TF displays show data. The Map display
will be empty until SLAM or AMCL is running.

- [ ] **Step 4: (Optional) Run SLAM on RPi and observe map building from workstation**

In an RPi terminal:
```bash
ssh rpi
source install/setup.bash && source scripts/setup_robot.sh
ros2 launch custom_tb4_bringup robot/slam.launch.py
```

In another workstation terminal, drive the robot with teleop:
```bash
cd ~/code/custom_turtlebot_nav_ws
source install/setup.bash && source scripts/setup_workstation.sh
ros2 run custom_tb4_autonomy teleop
# Press 'd' to undock, drive around with i/j/k/l/,
```

The map should appear in the RViz on the workstation.

- [ ] **Step 5: Save the map (on RPi)**

```bash
ssh rpi
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_environment
```

Expected: `~/maps/my_environment.pgm` and `~/maps/my_environment.yaml` exist.

---

## Phase 7: Final sync

### Task 21: Push everything to GitHub

- [ ] **Step 1: Push from workstation**

```bash
cd ~/code/custom_turtlebot_nav_ws
git status   # should be clean (everything committed)
git push origin main
```

- [ ] **Step 2: Verify on GitHub**

Open https://github.com/aod321/custom_turtlebot_nav_ws and check:
- README is the new role-oriented version
- `docs/specs/2026-04-08-multi-machine-deployment-design.md` exists
- `docs/plans/2026-04-08-multi-machine-deployment.md` exists (this file)
- `docs/troubleshooting.md` exists
- `docs/setup_new_robot.md` exists
- `CLAUDE.md` exists
- `scripts/*.sh` and `scripts/fastdds_discovery_server.service` exist
- `src/custom_tb4_bringup/launch/robot/` and `src/custom_tb4_bringup/launch/workstation/` directories populated

---

## Self-review checklist

**Spec coverage:**
- ✅ Topology + ROS_DOMAIN_ID=64 (Tasks 5–7, 15–18)
- ✅ Two RSPs coexist (already in workspace, no change)
- ✅ FastDDS Discovery Server systemd unit (Task 7)
- ✅ Create3 web config (Task 18)
- ✅ MJPG + image_transport_plugins (Task 4)
- ✅ Workspace launch split robot/ vs workstation/ (Tasks 1–3)
- ✅ default.rviz minimal (Task 2)
- ✅ setup scripts (Tasks 5–6)
- ✅ check_network.sh, smoke_test.sh (Tasks 8–9)
- ✅ README rewrite (Task 10)
- ✅ CLAUDE.md (Task 11)
- ✅ docs/troubleshooting.md (Task 12)
- ✅ docs/setup_new_robot.md (Task 13)
- ✅ Memory migration (Task 14)
- ✅ End-to-end verification (Tasks 19–20)
- ✅ Push to GitHub (Task 21)

**Gaps:**
- The `verify_handoff.sh` mentioned in spec §6.2 is the same as `smoke_test.sh`. Will create a one-line wrapper if needed in a follow-up.
- CI is explicitly out of scope per spec.
