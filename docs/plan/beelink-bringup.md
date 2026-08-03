---
title: "Beelink Bring-up"
type: plan
date: 2026-08-03
tags:
  - plan
  - hardware
  - bringup
  - migration
---

# Beelink Bring-up — replacing the Pi 5

The Raspberry Pi 5 ran out of CPU. Anything real — SLAM, Nav2, the dashboard,
the camera — pushed it to 100 % and the robot stopped being controllable. The
compute is being replaced by a **Beelink SER5 Pro**, and the Pi is coming off
the robot entirely.

This is the runbook to get from *a mini PC on a desk* to *a mini PC driving the
robot*. Work the stages in order. Stage 0 is the one that can destroy hardware.

Related: [[roadmap]] Phase 0 · [[inventory]] · [[system-overview]]

---

## Where things stand

**Measured on the Beelink, 2026-08-03:**

| | Pi 5 (removed) | Beelink SER5 Pro |
|---|---|---|
| CPU | 4 × Cortex-A76 @ 2.4 GHz | **8C/16T Ryzen 7 PRO 5800H** |
| Arch | aarch64 | **x86_64** |
| RAM | 7.8 GiB | **11.6 GiB** |
| Storage | 58 G SD card, 43 G free | **457 G NVMe, 425 G free** |
| GPU | VideoCore VII | **Radeon Vega (Cezanne)** |
| OS | Ubuntu 24.04.4 | Ubuntu 24.04.4 Server |

Roughly **4–6× the CPU**, and the architecture change matters as much as the
speed: on x86_64, librealsense, Nav2 and most ROS binaries are first-class
rather than an ARM afterthought.

**Done:** Ubuntu Server 24.04.4 installed, WiFi up (`wlo1`, 192.168.0.20),
GitHub SSH authenticating, repo cloned to `~/orbibot_ws`.

**Not done:** everything else. No ROS 2, no `colcon`, no `rosdep`, no
`gcc`/`cmake`, no `node`/`npm`, no PlatformIO. No robot hardware attached — no
LiDAR, no `/dev/motordriver`, no camera.

**Decisions taken 2026-08-03** (see [[roadmap]]):

- Power: **12 V battery → DC-DC boost → 19 V**, one battery for the whole robot
- The Pi 5 is **removed completely**, not kept as a second node
- The RealSense D435 runs **full depth**, not colour-only as on the Pi
- Simulation stays **optional and later** — not on the critical path

---

## Stage 0 — Power ⚠️

**Do this on a bench, with the Beelink disconnected, before anything is
mounted.** Getting the voltage wrong here destroys a mini PC in under a second.

### Parts

| Part | Spec |
|---|---|
| Boost converter | RBD-2767 — 150 W, 10–32 V in, 12–35 V out, 6 A (10 A with cooling) |
| Fuse | 10 A, **input side**, in the battery positive lead |
| Source | 4S LiFePO4 — 12.8 V nominal, 14.6 V full, 10.5 V cutoff |

### The load

> **Unverified — read the Beelink's power adapter label and confirm before
> wiring.** Everything below assumes **19 V / 3.42 A (65 W)**. Some Beelink
> models ship a 12 V brick, and if this one does, the boost converter is the
> wrong part and the whole stage changes.

Assuming 19 V / 65 W, at ~90 % converter efficiency:

| | Value |
|---|---|
| Output current at 19 V | 3.4 A — against a 6 A rating, comfortable |
| Input current at 12.8 V | ~5.6 A |
| Input current at 10.5 V (battery low) | ~6.9 A |

### Why the fuse goes on the input side

The 10 A fuse belongs in the **battery positive lead, as close to the battery
as practical**. On the input side it sees 5.6–6.9 A, so a 10 A fuse is a real
protection against a converter fault or a wiring short.

On the *output* side only 3.4 A ever flows — a 10 A fuse there would never
blow, and would protect nothing. Prefer a slow-blow fuse; the Beelink's
power-on inrush will nuisance-trip a fast one.

### Sequence — do not reorder

1. Battery **disconnected**. Wire the fuse into the battery positive lead, then
   the converter input. Leave the converter output **unconnected**.
2. Connect the battery. The converter's LED lights.
3. **Measure the output with a multimeter.** The multi-turn pot ships at an
   arbitrary setting — it could be 35 V.
4. Turn the pot until the output reads **19.0 V** (or whatever the label says).
   Multi-turn: it takes many rotations, and it is meant to.
5. Re-measure. Confirm it is stable and did not drift.
6. **Only now** connect the Beelink.

### What still has to be measured

**Battery sag is the open risk.** The converter's minimum input is 10 V and the
BMS cuts off at 10.5 V — a 0.5 V margin. Four motors pulling hard will dip the
rail transiently, and a brown-out while the NVMe is writing means a corrupt
filesystem, not just a reboot.

Before the robot drives on this rail, measure:

| # | Measurement | Pass |
|---|---|---|
| P-1 | Converter output under Beelink idle | 19 V ± 0.3 V |
| P-2 | Converter output during a 4-motor full-speed burst | stays > 18 V |
| P-3 | Battery terminal voltage during the same burst | stays > 11.5 V |
| P-4 | Converter case temperature after 30 min under load | < 70 °C |
| P-5 | Ten motor start/stop cycles, Beelink logged in | no reboot, no dmesg reset |

If P-2 or P-3 fails, the fixes in order of preference: bulk capacitance across
the converter input, thicker/shorter battery leads, or raising the software
low-voltage warning well above 10.5 V.

Record results in `test-report.md`, dated. See [[robot-safety]].

### Runtime

The battery holds **198.4 Wh**. Estimates only — measure them:

| State | Estimated draw | Estimated runtime |
|---|---|---|
| Idle, everything up, not driving | ~30 W | ~6.5 h |
| Driving with Nav2 + SLAM + dashboard | ~85 W | ~2.3 h |

The Beelink costs roughly 20–25 W more than the Pi did. That is the price of
the CPU, and it is worth it — but plan sessions around ~2 h of active driving,
not the Pi's numbers.

---

## Stage 1 — Base system

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  build-essential cmake git curl wget \
  python3-pip python3-venv python3-dev \
  v4l-utils usbutils net-tools htop
```

Ubuntu Server has no desktop, which is correct for a robot. RViz and any GUI
run on the operator's laptop over the network, not here.

---

## Stage 2 — ROS 2 Jazzy

Ubuntu 24.04 (noble) is Jazzy's native pairing, so everything comes from apt.

```bash
sudo add-apt-repository universe -y
sudo apt update && sudo apt install -y curl

# Current method — a .deb that installs the key and the source list
export ROS_APT_SOURCE_VERSION=$(curl -s \
  https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
  | grep -F "tag_name" | awk -F\" '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb"
sudo apt install -y /tmp/ros2-apt-source.deb

sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-dev-tools
```

`ros-base`, not `ros-desktop` — no GUI on the robot.

Then the packages this workspace actually needs:

```bash
sudo apt install -y \
  ros-jazzy-robot-localization \
  ros-jazzy-imu-filter-madgwick \
  ros-jazzy-slam-toolbox \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-rplidar-ros \
  ros-jazzy-rosbridge-suite \
  ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher \
  ros-jazzy-xacro ros-jazzy-tf-transformations \
  ros-jazzy-twist-mux
```

**`twist-mux` is on that list deliberately.** It was never installed on the Pi,
which is why four nodes publish `/cmd_vel` with nothing arbitrating —
[[backlog-moc]] CC-1, and the Phase 2 gate in [[roadmap]].

**Not installed, deliberately:** `ros-jazzy-joy`. Teleop is web-only.
`orbibot_teleop` stays dormant — see [[command-pipeline]].

---

## Stage 3 — Workspace build

```bash
sudo rosdep init && rosdep update
cd ~/orbibot_ws
rosdep install --from-paths src --ignore-src -r -y

source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Expect **12 packages**. The 13th, `orbibot_rosmaster_firmware`, carries a
`COLCON_IGNORE` — it is a PlatformIO project.

Add to `~/.bashrc`:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orbibot_ws/install/setup.bash
export ROS_DOMAIN_ID=42
```

Pick a `ROS_DOMAIN_ID` and use it on the laptop too, or RViz on the laptop will
not see the robot.

**Gate:** the workspace built clean on the Pi in ~40 s. On this machine it
should be faster. Any package that fails here fails because of an
architecture assumption — fix it, do not skip it.

---

## Stage 4 — Device naming

The stable-symlink rules are architecture-independent and already in the repo:

```bash
sudo ~/orbibot_ws/src/orbibot_hardware/scripts/setup_permissions.sh
```

This writes `/etc/udev/rules.d/99-orbibot.rules` (CH340 → `/dev/motordriver`,
CP210x → `/dev/lidar`, RealSense permissions) and adds the user to `dialout`,
`plugdev` and `video`. **Log out and back in** for the groups to take effect.

Verify after plugging the hardware in:

```bash
ls -l /dev/motordriver /dev/lidar
```

---

## Stage 5 — RealSense D435, with depth

This is the part the Pi could not do. On the Pi the D435 was stuck on a
480 Mbps link with no CPU to spare, so depth was disabled and the camera was
used as a plain webcam. On x86_64 with USB 3 and 16 threads, that constraint is
gone.

```bash
sudo apt install -y ros-jazzy-librealsense2 ros-jazzy-realsense2-camera
```

Confirm the link speed is **5000**, not 480 — plug into a blue port with a
USB 3-rated cable:

```bash
for d in /sys/bus/usb/devices/*/; do
  [ -f "$d/product" ] && echo "$(cat $d/product) — $(cat $d/speed) Mbps"
done | grep -i realsense
```

Until that reads 5000, depth and colour cannot run together at useful
resolution and the driver will silently drop stream combinations.

`realsense2_camera` on the Pi was a CPU disaster and [[dashboard-design]] says
to bypass it with v4l2. **That advice was Pi-specific.** With depth wanted, the
driver goes back in the graph — but the *dashboard* still gets its video over
WebRTC from v4l2, not by serialising `/camera/color/image_raw` through
rosbridge. Those are two separate paths and both are correct.

---

## Stage 6 — Firmware toolchain

The STM32 firmware still builds and flashes from the robot's computer.

```bash
python3 -m venv ~/.platformio-venv
~/.platformio-venv/bin/pip install platformio
```

The Pi used `~/.platformio/penv/bin/pio`. On this machine that path will differ
— **update `CLAUDE.md` and the firmware README with whatever path is real
here**, do not leave the Pi's path in the docs.

```bash
cd ~/orbibot_ws/src/orbibot_rosmaster_firmware
<pio> run          # build only; toolchain downloads on first run
```

Flashing still needs the manual BOOT0 jumper and RESET — the board has no
auto-bootloader circuit. That has not changed with the computer. See
[[robot-safety]].

---

## Stage 7 — Frontend toolchain

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
cd ~/orbibot_ws/src/orbibot_webgui/frontend
npm install && npm run build
```

Serve the built `dist/`. **Never run the Vite dev server on the robot** — it is
a file watcher with HMR, not a way to serve a dashboard. That rule survives the
CPU upgrade; it was never really about CPU.

---

## Stage 8 — Mounting

Only after Stages 0–7 pass on the bench.

1. Remove the Pi 5 and its 5 V feed from the ROSMaster board's Type-C.
2. Mount the Beelink. It is heavier and larger than the Pi — check that the
   350 × 250 mm footprint and the ~6 kg mass in [[inventory]] still hold, and
   re-measure if not. **A mass or centre-of-gravity change invalidates the
   Phase 1 odometry and PID numbers**, so measure before calibrating, not
   after.
3. Mount the converter where it can shed heat. It has heatsinks; buried under a
   deck with no airflow they do nothing.
4. Route the battery lead, fuse first, away from the motor leads.
5. USB: LiDAR and motor board on any port; **RealSense on a blue USB 3 port**.
6. Re-run Stage 4's verification with everything plugged in.

---

## Gate — Phase 0 is done when

- [ ] Adapter label read; converter output set and verified at that voltage
- [ ] P-1 … P-5 measured and recorded in `test-report.md`
- [ ] `colcon build` clean, 12 packages
- [ ] `/dev/motordriver` and `/dev/lidar` appear on boot
- [ ] RealSense enumerates at **5000 Mbps**, depth + colour stream together
- [ ] `ros2 launch orbibot_bringup robot.launch.py` runs, `/scan` at 10 Hz,
      `/odom` publishing
- [ ] Firmware builds with the new PlatformIO path
- [ ] Frontend `npm run build` produces `dist/`
- [ ] **New CPU baseline recorded** — the whole stack idle, and driving, so
      Phase 3 and Phase 6 have something real to budget against

That last one matters more than it looks. Every CPU number in
[[dashboard-design]] and every "reduced for Raspberry Pi" comment in
`nav2_params.yaml` and `slam_params.yaml` was tuned for a machine that is no
longer here. They are not just stale — they are actively holding the robot
back, and they cannot be re-derived without a baseline.

## Related

[[roadmap]] · [[inventory]] · [[system-overview]] · [[dashboard-design]] ·
[[command-pipeline]] · [[robot-safety]]
