# Sensors Issue Tracker

**Package:** `orbibot_sensors` (RPLidar A1, RealSense D435, obstacle detector)
**Last Updated:** 2026-08-04

---

## ✅ Resolved

### SENS-1: `/scan` runs at 7.9 Hz, not the documented 10 Hz
**Opened:** 2026-08-03 · **RESOLVED 2026-08-04** — the documentation was wrong
**Files:** `config/rplidar_params.yaml`, `launch/lidar.launch.py`

**Original report.** Measured on the Beelink with `robot.launch.py` up, robot
elevated, motors disabled:

```
ros2 topic hz /scan   →  average rate 7.911, 7.897
```

Documented as 10 Hz in `README.md`, [[system-overview]] and [[inventory]] —
21 % lower. Not a CPU problem: the machine was 98.6 % idle and
`rplidar_composition` used 0.6 % of one core, so it was a device or
configuration property, which also meant it was almost certainly true on the Pi
and simply never measured.

### Resolution: 8.0 Hz is the device, and the docs quoted the datasheet maximum

Measured 2026-08-04, robot elevated, each mode launched on its own:

| scan mode | rate | points / rev | angular resolution |
|---|---|---|---|
| Standard | 8.028 Hz | 360 | 1.000° |
| **Express** (in use) | **8.081 Hz** | **720** | **0.499°** |

**The rate does not change with the mode; the resolution does.** On an A1 the
scan rate is set by motor speed, and the mode selects how many samples are taken
per revolution. So Express is the right choice — same rate, double the angular
resolution — and it is already what the launch defaults to.

`docs/hardware/components.md` had it right the whole time: *"Scan Rate: 5.5 Hz
(configurable up to 10 Hz)"*. Every other document quoted the **10 Hz maximum as
the actual rate**. 8.0 Hz sits inside the device's range and is not a fault.

Corrected in `CLAUDE.md`, `system-overview`, `inventory`, both package READMEs,
`orbibot_slam`, `dashboard-design`, `computer-setup` and `baseline-results`.
`dashboard-design` was doubly wrong: it budgeted "~360 floats at 10 Hz" when
Express delivers 720.

**Boost, Sensitivity and Stability were not measured.** The device stopped
responding partway through the sweep and needed a USB replug. They are not
expected to change the rate — they trade sample density, not motor speed — but
that is reasoning, not measurement, and is recorded as such.

**Consequence for tuning.** `minimum_time_interval` in `slam_params.yaml` and
the costmap update rates in `nav2_params.yaml` were fitted against an assumed
10 Hz. Re-derive them against 8.0 — see [[inherited-values]]. Updating a costmap
faster than 8 Hz reprocesses the same scan.

---

## 🔴 Open

### SENS-2: RealSense D435 enumerates at 480 Mbps (USB 2.0)
**Opened:** 2026-08-03 · **Severity:** HIGH — blocks the depth decision
**Files:** hardware/cabling, `config/realsense_camera_params.yaml`

```
Intel(R) RealSense(TM) Depth Camera 435 — 480 Mbps
```

Depth was **enabled by decision on 2026-08-03**, and depth plus colour at useful
resolution needs a 5000 Mbps link. At 480 the driver silently drops or refuses
stream combinations rather than erroring.

**What has been tried, 2026-08-03 → 04:** two different blue ports, and two
cables including the one Intel shipped with the camera. Still 480 Mbps, still on
Bus 001.

**What the evidence says.** The camera's BOS descriptor advertises
*"can operate at SuperSpeed (5Gbps)"*, and the kernel logs `new high-speed USB
device` with no link-training errors — it never attempts SuperSpeed. Both
SuperSpeed root hubs, Bus 002 and Bus 004, are **completely empty and always
have been**.

That last fact is suggestive but **not** proof of a dead port: the camera is the
only USB 3 device on this machine, so if the camera or cable were at fault those
hubs would look identical. From software, "the port's SuperSpeed lanes are dead"
and "the cable has no SuperSpeed pairs" are indistinguishable.

**The one test that separates them:** plug any known USB 3 device — a USB 3 flash
drive — into the same blue port.

| result | conclusion |
|---|---|
| enumerates at 5000 | port is fine → camera or cable |
| enumerates at 480 | port or BIOS → check USB config in firmware setup |

```bash
for d in /sys/bus/usb/devices/*/; do
  [ -f "$d/product" ] && echo "$(cat $d/product) — $(cat $d/speed) Mbps"
done
lsusb -t   # anything on Bus 002 / Bus 004 is SuperSpeed
```

Deferred by the operator until the RealSense work block begins.

---

## See also

- `sensors-changelog.md` — what changed and why
- `docs/operations/baseline-results.md` — the measurements above, in context
- `docs/plan/inherited-values.md` — camera settings still fitted to the Pi
- `docs/moc/backlog-moc.md` — where every open finding lives
