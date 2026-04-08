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
