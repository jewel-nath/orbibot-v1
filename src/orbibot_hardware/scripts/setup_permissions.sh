#!/bin/bash

# OrbiBot Hardware Setup Script
# Sets up device permissions and installs dependencies

set -e

echo "=== OrbiBot Hardware Setup ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Run as your normal user — NOT with sudo.
#
# This script calls sudo itself for the three things that need root (the udev
# rules file, usermod, udevadm). It also reads $USER to decide which account
# joins dialout/plugdev/video, and under sudo that resolves to root — which
# would add the wrong account and leave the real one still unable to open
# /dev/motordriver.
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}Do not run this with sudo.${NC}"
   echo "Run it as your normal user: ./setup_permissions.sh"
   echo "It will prompt for sudo where it actually needs root."
   exit 1
fi

echo -e "${YELLOW}Setting up device permissions...${NC}"

# Create udev rules for OrbiBot hardware
UDEV_RULES_FILE="/etc/udev/rules.d/99-orbibot.rules"

sudo tee $UDEV_RULES_FILE > /dev/null <<EOF
# OrbiBot Hardware Device Rules
# Yahboom ROS expansion board (CH340 USB-Serial)
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="motordriver", MODE="0666", GROUP="dialout"

# RPLIDAR A1 (CP210x USB-Serial) 
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="lidar", MODE="0666", GROUP="dialout"

# Intel RealSense cameras
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b07", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0ad1", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0ad2", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0ad3", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0ad4", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b00", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b01", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b03", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b37", MODE="0666", GROUP="plugdev"
EOF

echo -e "${GREEN}✓ Created udev rules: $UDEV_RULES_FILE${NC}"

# Add user to required groups
echo -e "${YELLOW}Adding user to required groups...${NC}"
sudo usermod -a -G dialout,plugdev,video $USER

echo -e "${GREEN}✓ Added $USER to dialout, plugdev, and video groups${NC}"

# Reload udev rules
echo -e "${YELLOW}Reloading udev rules...${NC}"
sudo udevadm control --reload-rules
sudo udevadm trigger

echo -e "${GREEN}✓ Udev rules reloaded${NC}"

# Check Python dependencies
#
# Import name and apt package name differ, which is what made the old version
# of this check report a false failure: it ran `import pyserial`, but the
# module is `serial` — `pyserial` is only the distribution name. It reported
# "Failed to install pyserial" on a machine where pyserial 3.5 was installed
# and working.
echo -e "${YELLOW}Checking Python dependencies...${NC}"

# "import name:apt package"
PYTHON_DEPS=("serial:python3-serial" "numpy:python3-numpy")

for entry in "${PYTHON_DEPS[@]}"; do
    module="${entry%%:*}"
    apt_pkg="${entry##*:}"

    if python3 -c "import $module" 2>/dev/null; then
        echo -e "${GREEN}✓ $module ($apt_pkg) is installed${NC}"
        continue
    fi

    echo -e "${YELLOW}Installing $apt_pkg via apt...${NC}"
    sudo apt-get install -y "$apt_pkg"

    if python3 -c "import $module" 2>/dev/null; then
        echo -e "${GREEN}✓ $module installed successfully${NC}"
    else
        echo -e "${RED}✗ $module still not importable after installing $apt_pkg${NC}"
    fi
done

# NOTE: Yahboom's Rosmaster_Lib is deliberately NOT required. This project
# talks to the board with its own driver, orbibot_hardware/rosmaster_driver.py,
# which reimplements the protocol rather than wrapping the vendor library.
# An earlier version of this script told the operator to download and install
# Rosmaster_Lib from yahboom.net; nothing imports it.

# Check connected devices
echo -e "${YELLOW}Checking connected devices...${NC}"

if [ -e "/dev/motordriver" ]; then
    echo -e "${GREEN}✓ Motor driver found at /dev/motordriver${NC}"
else
    echo -e "${YELLOW}⚠ Motor driver not found at /dev/motordriver${NC}"
    echo "  Check USB connection and device ID"
fi

if [ -e "/dev/lidar" ]; then
    echo -e "${GREEN}✓ LIDAR found at /dev/lidar${NC}"
else
    echo -e "${YELLOW}⚠ LIDAR not found at /dev/lidar${NC}"
    echo "  Check USB connection and device ID"
fi

# List USB devices
echo -e "${YELLOW}Connected USB devices:${NC}"
lsusb | grep -E "(1a86|10c4|8086)"

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo -e "${YELLOW}Important Notes:${NC}"
echo "1. Log out and log back in (or reboot) for group changes to take effect"
echo "   (check with: id -nG  — dialout, plugdev and video must be listed)"
echo "2. Connect your OrbiBot hardware before launching"
echo ""
echo -e "${YELLOW}If Python dependency installation failed:${NC}"
echo "  sudo apt update"
echo "  sudo apt install python3-serial python3-numpy"
echo ""
echo -e "${YELLOW}Test hardware connection with:${NC}"
echo "  cd ~/orbibot_ws"
echo "  source install/setup.bash"
echo "  ros2 run orbibot_hardware hardware_test"
echo ""
echo -e "${YELLOW}Or check permissions with:${NC}"
echo "  ros2 run orbibot_hardware check_permissions"