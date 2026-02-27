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

# Check if running as root for udev rules
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root (except for udev rules)${NC}"
   echo "Run: sudo ./setup_permissions.sh"
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

# Check for ROSMaster_Lib
echo -e "${YELLOW}Checking for ROSMaster_Lib...${NC}"

if python3 -c "import Rosmaster_Lib" 2>/dev/null; then
    echo -e "${GREEN}✓ ROSMaster_Lib is already installed${NC}"
else
    echo -e "${RED}✗ ROSMaster_Lib not found${NC}"
    echo -e "${YELLOW}Please install ROSMaster_Lib manually:${NC}"
    echo "1. Download from: http://www.yahboom.net/study/ros-driver-board"
    echo "2. Extract and run: sudo python3 setup.py install"
    echo "3. Or install via pip if available"
fi

# Check Python dependencies
echo -e "${YELLOW}Checking Python dependencies...${NC}"

PYTHON_DEPS=("pyserial" "numpy")

for dep in "${PYTHON_DEPS[@]}"; do
    if python3 -c "import $dep" 2>/dev/null; then
        echo -e "${GREEN}✓ $dep is installed${NC}"
    else
        echo -e "${YELLOW}Installing $dep via apt...${NC}"
        # Try apt first (Ubuntu 24.04 preferred method)
        if [ "$dep" = "pyserial" ]; then
            sudo apt install -y python3-serial
        elif [ "$dep" = "numpy" ]; then
            sudo apt install -y python3-numpy
        fi
        
        # Verify installation
        if python3 -c "import $dep" 2>/dev/null; then
            echo -e "${GREEN}✓ $dep installed successfully${NC}"
        else
            echo -e "${RED}✗ Failed to install $dep${NC}"
            echo -e "${YELLOW}You may need to install manually:${NC}"
            echo "  sudo apt install python3-$dep"
        fi
    fi
done

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
echo "2. Verify ROSMaster_Lib installation before running hardware node"
echo "3. Connect your OrbiBot hardware before launching"
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