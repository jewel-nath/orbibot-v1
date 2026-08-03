# Sensors Issue Tracker

**Package:** `orbibot_sensors` (RPLidar A1, RealSense D435, obstacle detector)
**Last Updated:** 2026-08-03

---

## 🔴 Open

### SENS-1: `/scan` runs at 7.9 Hz, not the documented 10 Hz
**Opened:** 2026-08-03 · **Severity:** MEDIUM
**Files:** `config/rplidar_params.yaml`, `launch/lidar.launch.py`

Measured on the Beelink with `robot.launch.py` up, robot elevated, motors
disabled:

```
ros2 topic hz /scan   →  average rate 7.911, 7.897
```

Documented as 10 Hz in `README.md`, [[system-overview]] and [[inventory]].
Actual is **21 % lower**.

**Not a CPU problem.** The machine was 98.6 % idle during the measurement and
`rplidar_composition` used 0.6 % of one core. This is a device or configuration
property, not contention — which also means it was almost certainly true on the
Pi and simply never measured.

The node reports `current scan mode: Express, max_distance: 12.0 m, Point
number: 3.9K, angle_compensate: 1`. Scan rate on an A1 is set by motor PWM and
trades against points-per-revolution, so `Express` at 3.9K points may simply not
sustain 10 Hz.

**Why it matters:** Nav2's controller frequency, the costmap update rate and
slam_toolbox's `minimum_time_interval` are all tuned against an assumed scan
rate. Phase 5 and Phase 6 must not be tuned against 10 Hz while the sensor
delivers 7.9.

**How to resolve:**
1. Try `scan_mode: Standard` / `Boost` and re-measure — record points/rev too
2. If 10 Hz is not achievable, **fix the documentation, not the number** —
   update README, `system-overview` and `inventory` to the measured rate
3. Either way, record the final figure with its scan mode

---

### SENS-2: RealSense D435 enumerates at 480 Mbps (USB 2.0)
**Opened:** 2026-08-03 · **Severity:** HIGH — blocks the depth decision
**Files:** hardware/cabling, `config/realsense_camera_params.yaml`

```
Intel(R) RealSense(TM) Depth Camera 435 — 480 Mbps
```

Depth was **enabled by decision on 2026-08-03**, and depth plus colour at useful
resolution needs a 5000 Mbps link. At 480 the driver silently drops or refuses
stream combinations rather than erroring.

`lsusb` shows the camera on Bus 001, a 2.0 root hub. The Beelink has **two idle
USB 3 root hubs** (Bus 002 and Bus 004). This is the same condition the Pi had,
and the reason depth was switched off there — it followed the camera across the
migration because it is a cabling property, not a host one.

**How to resolve:** move to a blue USB 3 port with a USB 3-rated cable, then:

```bash
for d in /sys/bus/usb/devices/*/; do
  [ -f "$d/product" ] && echo "$(cat $d/product) — $(cat $d/speed) Mbps"
done | grep -i realsense
```

Must read **5000**. A worn or USB-2-only cable will keep it at 480 whatever port
it is in.

---

## See also

- `sensors-changelog.md` — what changed and why
- `docs/operations/baseline-results.md` — the measurements above, in context
- `docs/moc/backlog-moc.md` — where every open finding lives
