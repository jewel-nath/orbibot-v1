#!/bin/bash
# OrbiBot safety parameter validation

set -e

ISSUES=0
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HARDWARE_CONFIG="$ROOT/src/orbibot_hardware/config/hardware_params.yaml"
FIRMWARE_CONFIG="$ROOT/src/orbibot_rosmaster_firmware/include/orbibot_config.h"

echo "OrbiBot Safety Check"
echo "===================="
echo ""

# Velocity Limits
echo "[Velocity Limits]"
if [ -f "$HARDWARE_CONFIG" ]; then
    MAX_LIN=$(grep -E "max_linear_velocity:" "$HARDWARE_CONFIG" 2>/dev/null | awk '{print $2}')
    MAX_ANG=$(grep -E "max_angular_velocity:" "$HARDWARE_CONFIG" 2>/dev/null | awk '{print $2}')

    if [ -n "$MAX_LIN" ]; then
        if (( $(echo "$MAX_LIN > 1.0" | bc -l) )); then
            echo "  Linear: ${MAX_LIN} m/s - WARNING (>1.0)"
            ISSUES=$((ISSUES + 1))
        else
            echo "  Linear: ${MAX_LIN} m/s - OK"
        fi
    else
        echo "  Linear: not set - ERROR"
        ISSUES=$((ISSUES + 1))
    fi

    if [ -n "$MAX_ANG" ]; then
        if (( $(echo "$MAX_ANG > 2.0" | bc -l) )); then
            echo "  Angular: ${MAX_ANG} rad/s - WARNING (>2.0)"
            ISSUES=$((ISSUES + 1))
        else
            echo "  Angular: ${MAX_ANG} rad/s - OK"
        fi
    else
        echo "  Angular: not set - ERROR"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo "  Config not found: $HARDWARE_CONFIG"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# Battery Thresholds (4S LiFePO4: nominal 12.8V)
echo "[Battery Thresholds]"
if [ -f "$HARDWARE_CONFIG" ]; then
    BAT_LOW=$(grep -E "battery_low_voltage:" "$HARDWARE_CONFIG" 2>/dev/null | awk '{print $2}')
    BAT_CRIT=$(grep -E "battery_critical_voltage:" "$HARDWARE_CONFIG" 2>/dev/null | awk '{print $2}')

    [ -n "$BAT_LOW" ] && echo "  Low warning: ${BAT_LOW}V" || echo "  Low warning: not set"
    [ -n "$BAT_CRIT" ] && echo "  Critical: ${BAT_CRIT}V" || echo "  Critical: not set"
fi
echo ""

# Firmware Safety
echo "[Firmware Safety]"
if [ -f "$FIRMWARE_CONFIG" ]; then
    TIMEOUT=$(grep -E "#define.*MOTOR_TIMEOUT" "$FIRMWARE_CONFIG" 2>/dev/null | awk '{print $3}')
    WATCHDOG=$(grep -E "#define.*WATCHDOG_ENABLE" "$FIRMWARE_CONFIG" 2>/dev/null | grep -v "//")

    if [ -n "$TIMEOUT" ]; then
        echo "  Motor timeout: ${TIMEOUT}ms"
        [ "$TIMEOUT" -gt 1000 ] && echo "    WARNING: >1000ms is too long" && ISSUES=$((ISSUES + 1))
    else
        echo "  Motor timeout: not set - WARNING"
    fi

    [ -n "$WATCHDOG" ] && echo "  Watchdog: enabled" || echo "  Watchdog: not found"
else
    echo "  Config not found: $FIRMWARE_CONFIG"
fi
echo ""

# Serial Access
echo "[Serial Access]"
if [ -e "/dev/motordriver" ]; then
    if [ -r "/dev/motordriver" ] && [ -w "/dev/motordriver" ]; then
        echo "  /dev/motordriver: OK (read/write)"
    else
        echo "  /dev/motordriver: NO ACCESS - add user to dialout group"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo "  /dev/motordriver: not connected"
fi
echo ""

# Summary
echo "===================="
if [ $ISSUES -eq 0 ]; then
    echo "All checks passed"
    exit 0
else
    echo "Found $ISSUES issue(s)"
    exit 1
fi
