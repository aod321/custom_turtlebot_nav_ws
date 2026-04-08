#!/usr/bin/env bash
# Run ON THE RPi (one time). Replaces /etc/ros/humble/turtlebot4.d/standard.launch.py
# with a version that does NOT include the system turtlebot4_description launch,
# so the only robot_state_publisher running is ours (custom_tb4_description),
# which publishes the correct URDF for the bare Create3 + custom sensor mount.
#
# Backs up the original to standard.launch.py.bak.
set -e

SYSTEM_LAUNCH=/etc/ros/humble/turtlebot4.d/standard.launch.py
BACKUP=$SYSTEM_LAUNCH.bak

if [ ! -f "$SYSTEM_LAUNCH" ]; then
    echo "ERROR: $SYSTEM_LAUNCH not found. Is turtlebot4 service installed?"
    exit 1
fi

if [ ! -f "$BACKUP" ]; then
    echo "Backing up $SYSTEM_LAUNCH -> $BACKUP"
    sudo cp "$SYSTEM_LAUNCH" "$BACKUP"
else
    echo "Backup already exists at $BACKUP (not overwriting)"
fi

# Patch: comment out the description_launch_file include block.
sudo python3 - "$SYSTEM_LAUNCH" << 'PYEOF'
import sys
path = sys.argv[1]
with open(path) as f:
    text = f.read()

old = """            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([description_launch_file]),
                launch_arguments=[('model', 'standard')]),
"""
new = """            # Disabled by custom_turtlebot_nav_ws install_description_override.sh:
            # the system turtlebot4_description provides a URDF that assumes the
            # standard turtlebot4 shell + sensor mounts, which conflicts with our
            # bare Create3 + custom sensor build. Our own RSP is started by
            # custom_tb4_description/launch/description.launch.py instead.
            # IncludeLaunchDescription(
            #     PythonLaunchDescriptionSource([description_launch_file]),
            #     launch_arguments=[('model', 'standard')]),
"""

if new.strip() in text:
    print("Override already applied, nothing to do")
elif old in text:
    text = text.replace(old, new)
    with open(path, 'w') as f:
        f.write(text)
    print("Override applied")
else:
    print("ERROR: expected description_launch_file include block not found.")
    print("The system file may have been updated. Please review manually.")
    sys.exit(2)
PYEOF

echo
echo "Done. Now restart the turtlebot4 service:"
echo "  sudo systemctl restart turtlebot4.service"
echo
echo "And make sure your custom_tb4_description launch is started, e.g. via"
echo "  ros2 launch custom_tb4_bringup robot_sensors.launch.py"
