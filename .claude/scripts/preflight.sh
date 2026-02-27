#!/bin/bash
# OrbiBot pre-flight check - run before operating the robot

echo "OrbiBot Pre-Flight Check"
echo "========================"

PASS=0
FAIL=0

check() {
    if $2; then
        echo "  [OK] $1"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $1"
        FAIL=$((FAIL + 1))
    fi
}

# Hardware
echo ""
echo "[Hardware]"
check "Motor driver connected" "[ -e /dev/motordriver ]"
check "Serial access" "[ -r /dev/motordriver ] && [ -w /dev/motordriver ]"

# ROS 2
echo ""
echo "[ROS 2]"
check "ROS_DISTRO set" "[ -n \"$ROS_DISTRO\" ]"
check "Workspace sourced" "[ -f install/setup.bash ]"

# Battery (if topic available)
echo ""
echo "[Battery]"
if timeout 2 ros2 topic echo /orbibot/battery --once &>/dev/null; then
    VOLTAGE=$(timeout 2 ros2 topic echo /orbibot/battery --once 2>/dev/null | grep voltage | awk '{print $2}')
    if [ -n "$VOLTAGE" ]; then
        if (( $(echo "$VOLTAGE > 11.0" | bc -l 2>/dev/null || echo 0) )); then
            echo "  [OK] Battery: ${VOLTAGE}V"
            PASS=$((PASS + 1))
        else
            echo "  [FAIL] Battery low: ${VOLTAGE}V"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "  [SKIP] Could not read voltage"
    fi
else
    echo "  [SKIP] Battery topic not available"
fi

# Key nodes
echo ""
echo "[Nodes]"
if ros2 node list &>/dev/null; then
    NODES=$(ros2 node list 2>/dev/null)
    [ -n "$(echo "$NODES" | grep hardware_node)" ] && echo "  [OK] hardware_node" && PASS=$((PASS+1)) || echo "  [WARN] hardware_node not running"
else
    echo "  [SKIP] ROS 2 not running"
fi

# Summary
echo ""
echo "========================"
echo "Passed: $PASS  Failed: $FAIL"

if [ $FAIL -eq 0 ]; then
    echo "Ready to operate"
    exit 0
else
    echo "Fix issues before operating"
    exit 1
fi
