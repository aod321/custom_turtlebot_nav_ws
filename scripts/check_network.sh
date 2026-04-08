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
