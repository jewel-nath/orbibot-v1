#!/bin/bash
# OrbiBot quick motor test - spins each wheel briefly

echo "OrbiBot Motor Test"
echo "=================="
echo ""
echo "This will briefly spin each motor."
echo "Ensure robot is elevated or wheels are free!"
echo ""
read -p "Press Enter to start (Ctrl+C to cancel)..."

# Check if test script exists
TEST_SCRIPT="src/orbibot_rosmaster_firmware/tests/test_motor_direction.py"

if [ ! -f "$TEST_SCRIPT" ]; then
    echo "Error: Motor test script not found"
    echo "Expected: $TEST_SCRIPT"
    exit 1
fi

# Check hardware
if [ ! -e "/dev/motordriver" ]; then
    echo "Error: Motor driver not connected"
    exit 1
fi

echo ""
echo "Running motor direction test..."
python3 "$TEST_SCRIPT" --port /dev/motordriver

echo ""
echo "Done. Check that all 4 wheels responded correctly."
