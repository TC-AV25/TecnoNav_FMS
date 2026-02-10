#!/bin/bash
# Zenoh-based CPU bridge - runs in FMS environment using zenoh_ros_type
# This directly publishes CPU usage to Zenoh (not through ROS2)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_SCRIPT="$SCRIPT_DIR/zenoh_cpu_bridge.py"

# Find FMS directory
FMS_DIR="/media/adone/TC1/Projects/TecnoNav/zenoh/zenoh_autoware_fms"

if [ ! -d "$FMS_DIR" ]; then
    echo "❌ Error: FMS directory not found at $FMS_DIR"
    exit 1
fi

if [ ! -f "$BRIDGE_SCRIPT" ]; then
    echo "❌ Error: Bridge script not found at $BRIDGE_SCRIPT"
    exit 1
fi

echo "🚀 Starting Zenoh CPU Bridge"
echo ""
echo "Configuration:"
echo "  Bridge Script: $BRIDGE_SCRIPT"
echo "  FMS Directory: $FMS_DIR"
echo "  FMS Virtual Env: $FMS_DIR/.venv"
echo ""
echo "This bridge uses zenoh_ros_type from FMS environment"
echo "Publishing CPU usage directly to Zenoh at 172.30.10.52:7887"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Activate FMS virtual environment and run bridge
cd "$FMS_DIR"

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "❌ Error: FMS virtual environment not found"
    echo "Please run: cd $FMS_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
    exit 1
fi

# Run in FMS venv with zenoh_ros_type available
source .venv/bin/activate
python3 "$BRIDGE_SCRIPT"
