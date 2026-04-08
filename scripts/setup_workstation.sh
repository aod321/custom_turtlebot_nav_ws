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

# Override /tf reader QoS to BEST_EFFORT so kill/restart cycles don't
# accumulate phantom RELIABLE readers on Create3's writer and stall it.
# See scripts/fastdds_qos_override.xml for the full rationale.
_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
export FASTRTPS_DEFAULT_PROFILES_FILE="${_script_dir}/fastdds_qos_override.xml"
unset _script_dir

echo "[setup_workstation] ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo "[setup_workstation] ROS_DISCOVERY_SERVER=$ROS_DISCOVERY_SERVER"
echo "[setup_workstation] ROS_SUPER_CLIENT=$ROS_SUPER_CLIENT"
echo "[setup_workstation] RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
