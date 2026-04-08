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

## 3. RPi: clone the workspace and install the discovery server

```bash
ssh rpi
git clone https://github.com/aod321/custom_turtlebot_nav_ws.git ~/custom_turtlebot_nav_ws
cd ~/custom_turtlebot_nav_ws
./scripts/install_discovery_server.sh
```

Verify it's running and listening:
```bash
sudo systemctl status fastdds_discovery_server
sudo ss -tlnp | grep 11811
```

## 4. RPi: edit `/etc/turtlebot4/setup.bash`

Back up the original, then change/add these env vars so the system
turtlebot4 service joins the discovery server.

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
git clone https://github.com/aod321/custom_turtlebot_nav_ws.git ~/code/custom_turtlebot_nav_ws
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
