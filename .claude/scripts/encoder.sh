#!/bin/bash
# Diagnose encoder communication failures

echo "Encoder Diagnostic"
echo "=================="
echo ""

# Check hardware_node
echo "[Hardware Node]"
if ros2 node list 2>/dev/null | grep -q "/hardware_node"; then
    echo "  Status: running"
else
    echo "  Status: NOT RUNNING"
    echo "  Start: ros2 launch orbibot_bringup system.launch.py"
    exit 1
fi
echo ""

# Check serial
echo "[Serial Connection]"
if [ -e "/dev/motordriver" ]; then
    echo "  Device: /dev/motordriver exists"
else
    echo "  Device: NOT FOUND"
    ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | sed 's/^/  Available: /' || echo "  No USB serial devices"
    exit 1
fi
echo ""

# Check encoder topic
echo "[Encoder Topic]"
if ros2 topic list 2>/dev/null | grep -q "/orbibot/encoders"; then
    echo "  Topic: exists"
    echo "  Reading data (5s timeout)..."
    if timeout 5 ros2 topic echo /orbibot/encoders --once 2>/dev/null; then
        echo "  Data: OK - encoders working"
        exit 0
    else
        echo "  Data: NO RESPONSE"
    fi
else
    echo "  Topic: NOT FOUND"
fi
echo ""

# Troubleshooting
echo "[Troubleshooting]"
echo "  1. Check USB cable"
echo "  2. Verify STM32 has power"
echo "  3. Check BOOT0 is LOW (run mode)"
echo "  4. Press RESET on board"
echo "  5. Restart hardware_node"
echo "  6. Check encoder wiring (M1-M4)"
