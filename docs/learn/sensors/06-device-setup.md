---
title: "06 - Device Setup"
type: learn
area: sensors
package: orbibot_sensors
tags:
  - learn
  - sensors
---

# 06 - Device Setup

**udev rules and permissions**

---

## 🎯 Learning Objectives

- Create udev rules for sensors
- Understand device permissions
- Troubleshoot device issues

---

## 🔌 USB Devices

OrbiBot uses three USB devices:

| Device | Vendor:Product | Symlink |
|--------|---------------|---------|
| RPLidar A1 | 10c4:ea60 | /dev/lidar |
| RealSense D435 | 8086:0b07 | /dev/camera |
| Motor Driver (CH340) | 1a86:7523 | /dev/motordriver |

---

## 📝 udev Rules

Create `/etc/udev/rules.d/99-orbibot.rules`:

```bash
# RPLidar A1
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", \
  ATTRS{idProduct}=="ea60", SYMLINK+="lidar", \
  MODE="0666", GROUP="dialout"

# RealSense D435
SUBSYSTEM=="usb", ATTR{idVendor}=="8086", \
  ATTR{idProduct}=="0b07", SYMLINK+="camera", \
  MODE="0666", GROUP="dialout"

# Motor driver
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", \
  ATTRS{idProduct}=="7523", SYMLINK+="motordriver", \
  MODE="0666", GROUP="dialout"
```

---

## 🔄 Apply Rules

```bash
# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Verify
ls -la /dev/lidar /dev/camera /dev/motordriver
```

---

## 🎯 Key Takeaways

1. **udev rules** = Persistent device names
2. **Symlinks** = Easy-to-remember paths
3. **Permissions** = Allow user access
4. **Reload** = Apply without reboot

---

**OrbiBot Sensors Guide Complete!**

---

*Last Updated: March 2026*