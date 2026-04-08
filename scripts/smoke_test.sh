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
if nc -zuvw 2 192.168.111.230 11811 >/dev/null 2>&1; then
    ok "discovery server port open"
else
    bad "discovery server unreachable at 192.168.111.230:11811"
    echo "  -> On RPi run: sudo systemctl status fastdds_discovery_server"
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

if timeout 3 ros2 topic hz /camera/image_raw 2>&1 | grep -q "average rate"; then
    ok "/camera/image_raw streaming (compressed transport loads on demand)"
else
    warn "/camera/image_raw NOT streaming (run robot_sensors.launch.py on RPi?)"
fi

echo
echo "=== Summary ==="
echo "  passed: $PASS"
echo "  failed: $FAIL"
[ "$FAIL" -eq 0 ] && { echo "SMOKE TEST PASSED"; exit 0; } || { echo "SMOKE TEST FAILED"; exit 1; }
