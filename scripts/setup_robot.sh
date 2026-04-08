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

# Override /tf reader QoS to BEST_EFFORT so kill/restart cycles don't
# accumulate phantom RELIABLE readers on Create3's writer and stall it.
# See scripts/fastdds_qos_override.xml for the full rationale.
_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
export FASTRTPS_DEFAULT_PROFILES_FILE="${_script_dir}/fastdds_qos_override.xml"
unset _script_dir

echo "[setup_robot] ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo "[setup_robot] ROS_DISCOVERY_SERVER=$ROS_DISCOVERY_SERVER"
echo "[setup_robot] RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
