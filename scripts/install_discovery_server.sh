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
