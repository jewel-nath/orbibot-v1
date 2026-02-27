#!/bin/bash
# OrbiBot diagnostic script - collects system status for troubleshooting

set -e

echo "OrbiBot Diagnostic Report"
echo "========================="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ROS 2 Environment
echo "[ROS 2 Environment]"
echo "  ROS_DISTRO: ${ROS_DISTRO:-not set}"
echo "  RMW: ${RMW_IMPLEMENTATION:-default}"
echo ""

# Active Nodes
echo "[Active Nodes]"
if ros2 node list &>/dev/null; then
    ros2 node list 2>/dev/null | sed 's/^/  /' || echo "  none"
else
    echo "  ROS 2 not running"
fi
echo ""

# Key Topics
echo "[Topic Status]"
TOPICS=("/odom" "/orbibot/encoders" "/imu/data" "/cmd_vel")
for topic in "${TOPICS[@]}"; do
    if timeout 2 ros2 topic info "$topic" &>/dev/null; then
        echo "  $topic: OK"
    else
        echo "  $topic: not available"
    fi
done
echo ""

# Hardware Connection
echo "[Hardware]"
if [ -e "/dev/motordriver" ]; then
    echo "  Motor driver: connected"
else
    echo "  Motor driver: NOT FOUND"
    ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | sed 's/^/  Available: /' || echo "  No USB serial devices"
fi
echo ""

# System Resources
echo "[System]"
echo "  CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}')%"
echo "  Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "  Disk: $(df -h / | awk 'NR==2 {print $5 " used"}')"
if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
    TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
    echo "  Temp: $((TEMP/1000))C"
fi
echo ""

# Recent Errors
echo "[Recent Errors]"
if systemctl is-active --quiet orbibot.service 2>/dev/null; then
    journalctl -u orbibot.service --since "5 min ago" 2>/dev/null | grep -iE "error|fail" | tail -5 || echo "  none"
else
    dmesg | grep -iE "usb.*error|serial.*error" | tail -3 || echo "  none"
fi

echo ""
echo "Done."
