#!/bin/bash
# OrbiBot wheel-direction check — commands whole-robot motion and reads encoders.
#
# This used to run tests/test_motor_direction.py, which drove each wheel through
# a "SET_MOTOR" function code that does not exist in this firmware. Every packet
# was rejected on its length check, no motor was ever commanded, and the script
# then asked the operator whether the wheel had spun. See firmware-issue.md
# FW-ISSUE-12.
#
# test_kinematics.py checks the same thing the way the protocol actually allows:
# command a pure vx / vy / wz via FUNC_MOTION (0x12) and read which encoders
# move. It reports ticks, so nothing depends on a human judging a spinning wheel.

set -uo pipefail

echo "OrbiBot Wheel Direction Check"
echo "============================="
echo ""
echo "This spins all four wheels — 2 s per direction, four directions."
echo ""
echo "!! THE ROBOT MUST BE ELEVATED, WHEELS FREE !!"
echo ""
echo "Stop it at any time with Ctrl+C, or cut power at the battery."
echo ""
read -r -p "Robot elevated and wheels free? Press Enter to start, Ctrl+C to cancel..."

TEST_SCRIPT="src/orbibot_rosmaster_firmware/tests/test_kinematics.py"

if [ ! -f "$TEST_SCRIPT" ]; then
    echo "Error: test script not found at $TEST_SCRIPT"
    echo "Run this from the workspace root."
    exit 1
fi

if [ ! -e /dev/motordriver ]; then
    echo "Error: /dev/motordriver not present — is the board connected and powered?"
    exit 1
fi

# A ROS 2 stack holding the port makes this fail in a way that looks like a
# hardware fault. Check before blaming the board.
if [ -x .claude/scripts/stop.sh ]; then
    if ! .claude/scripts/stop.sh --check | grep -q "Nothing running"; then
        echo ""
        echo "Something is already running and may be holding /dev/motordriver:"
        .claude/scripts/stop.sh --check
        echo ""
        read -r -p "Continue anyway? [y/N] " reply
        [ "$reply" = "y" ] || exit 1
    fi
fi

echo ""
python3 "$TEST_SCRIPT" --port /dev/motordriver
status=$?

echo ""
echo "Expected sign pattern — see test-report.md §6:"
echo "  Forward (+Vx)        FL+  BL+  FR+  BR+"
echo "  Backward (-Vx)       FL-  BL-  FR-  BR-"
echo "  Left     (+Vy)       FL-  BL+  FR+  BR-"
echo "  Rotate CCW (+wz)     FL-  BL-  FR+  BR+"
echo ""
echo "Record the result in docs/operations/test-index.md, and any measured"
echo "numbers in src/orbibot_rosmaster_firmware/test-report.md with the date."
exit $status
