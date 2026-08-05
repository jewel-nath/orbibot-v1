---
title: "Physical Checks"
type: operations
tags:
  - operations
  - testing
  - hardware
---

# Physical checks — what only the real robot can confirm

Everything in this file is a claim the software **cannot verify about itself**.
The code can tell you M4 is 12–15 % slow; it cannot tell you M4 is the
back-right wheel. It can report a wheel radius of 50 mm; it cannot notice that
the tyre squashes to 48 mm under 6 kg. It can publish a TF tree; it cannot see
that the LiDAR is bolted on backwards.

Each of these is **100 % settleable by looking, measuring or touching** — no
inference, no statistics. That is the point: they are the assumptions
everything else is built on, and they are the ones most likely to be wrong
without anything failing loudly.

**How to use this file.** Run `/robot-check` and it will walk you through a
section one item at a time, or work down it yourself and fill in the last two
columns as you go — date and what you found. Write the **number**, not "ok". A row that
says `2026-08-04 · 99 mm` is worth something next year; a row that says `✅` is
not.

> Related but different: [[test-index]] lists what to **run**.
> This file lists what to **look at**. A test can pass against a wrong
> assumption; that is precisely what this file exists to catch.

---

## A · Look at it — no tools, no power

| # | Confirm | How | Wrong ⇒ what breaks | Checked | Found |
|---|---|---|---|---|---|
| A1 | **Mecanum rollers form an X seen from above** (ABBA) | Look down at all four wheels. Front-left and back-right rollers run one way; front-right and back-left the other | Sideways motion goes the wrong way, or the robot crabs when told to go straight. Kinematics cannot detect it | — | |
| A2 | **M1=FL, M2=BL, M3=FR, M4=BR** | Trace each motor cable to its board connector, or drive one motor at a time and watch which wheel turns | FW-ISSUE-4 says "M4 is 12–15 % slow". Useless until M4 is known to be the **back-right** wheel. Every per-wheel fix depends on this | — | |
| A3 | **LiDAR 0° points forward (+X)** | Find the marker on the A1 housing; it must face the robot's front | Obstacles appear rotated. SLAM builds a consistent but wrong map, and nothing errors | — | |
| A4 | **ROSMaster board is not rotated w.r.t. the chassis** | Board's own X/Y must line up with robot forward/left | roll and pitch swap through the whole pipeline; URDF says `rpy="0 0 0"` | ✅ 2026-08-04 | not rotated — moved rearward only |
| A5 | **Fuse is 10 A and on the converter *input*** | Follow the wire from the battery: fuse must come **before** the RBD-2767 | A fuse on the output does not protect the battery-side short, which is the one that matters | — | |
| A6 | **BOOT0 jumper is LOW (GND)** | Look at the jumper on the ROSMaster | Board boots into the bootloader and never runs firmware. Looks identical to "board is dead" | — | |
| A7 | **RealSense faces forward and is level** | Eye-line along the lens housing | Depth→costmap projection is skewed; obstacles land in the wrong place | — | |
| A8 | **No cable can reach a wheel or a roller** | Tug-test every loom; check slack near the wheel arches | A cable in a mecanum roller stops the robot mid-drive and can strip a motor | — | |
| A9 | **Nothing is resting on the Beelink's fan intake** | Look | Thermal throttling that reads as "the software got slower" | — | |

---

## B · Tape measure, calipers, kitchen scale

Every number here is currently in `CLAUDE.md` or the URDF as an **inherited
figure**, not a measured one. All of them change when the Beelink is mounted.

| # | Confirm | Claimed | How | Wrong ⇒ what breaks | Checked | Found |
|---|---|---|---|---|---|---|
| B1 | **Wheel radius, unloaded** | 50 mm (100 mm dia.) | Calipers across the wheel, off the ground | Odometry scales by the error — 2 % here is 2 % on every distance | — | |
| B2 | **Wheel radius, loaded** | *not recorded* | Measure axle height above the floor with the robot standing, ×1 | The rolling radius is the loaded one. Using the unloaded figure makes the robot think it went further than it did | — | |
| B3 | **Wheelbase** (front axle ↔ rear axle) | 260 mm | Tape, centre to centre | Rotation and strafe kinematics; yaw from wheels comes out wrong | — | |
| B4 | **Track** (left wheel ↔ right wheel) | 360 mm | Tape, centre to centre | Same as B3 | — | |
| B5 | **Footprint** | 350 × 250 mm | Tape over the widest points | Nav2 inflation and clearance. Too small and it clips doorframes | — | |
| B6 | **Mass** | ~6 kg | Kitchen/luggage scale, robot complete | PID response and traction. Must be re-taken **after** the Beelink, converter and fuse are on | — | |
| B7 | **IMU offset from `base_link`** | `0, 0, 0.02` | Tape from the chassis reference point to the IMU chip | DESC-1. Matters during turns: a lever arm `d` adds ω²d that Madgwick reads as tilt | — | |
| B8 | **LiDAR offset and height** | see URDF | Tape | Scans land at the wrong place in the map | — | |
| B9 | **Camera offset and height** | see URDF | Tape | Depth obstacles land at the wrong place | — | |
| B10 | **Ground → `base_link` height** | see URDF | Tape, robot standing | `base_footprint` is the frame everything navigates in | — | |

> Take B1 and B2 on **all four wheels**, not one. A single squashed or
> mis-seated tyre shows up as a persistent curve in odometry and gets blamed on
> the gyro.

---

## C · Multimeter

**Order matters — see `.claude/rules/robot-safety.md`.** Never connect the
Beelink before C2 reads correctly.

| # | Confirm | How | Wrong ⇒ what breaks | Checked | Found |
|---|---|---|---|---|---|
| C1 | **Reported battery voltage matches reality** | Multimeter across the pack vs `ros2 topic echo /orbibot/system_status` | The 11.0 V warning and 10.5 V cutoff are only as good as the ADC. A 0.4 V offset means the cutoff fires late — into a brown-out | ✅ 2026-08-04 | meter **12.95 V**, firmware **12.700 V** → offset **−0.25 V**, reads low. Thresholds fire **early** — the safe direction. §9.10 |
| C2 | **Converter output is 19.0 V, before the Beelink is connected** (P-1) | Multimeter on the RBD-2767 output, adjust the pot | The pot ships anywhere in a range that reaches 35 V. Connecting first can destroy the computer | — | |
| C3 | **Converter case temperature after 30 min under load** (P-4) | Touch/IR thermometer | A converter that runs hot fails later, on the floor, mid-drive | — | |
| C4 | **Battery rail under a four-motor burst** (P-3) | ~~Multimeter~~ — C1 removed the meter from this loop. `python3 .claude/scripts/drive_profile.py -p sprint -b 0.8`, wheels **on the ground**, ~1 m clear | The converter's 10 V minimum sits **0.71 V** below where the BMS cutoff really fires (C1). A dip during an NVMe write corrupts the filesystem | ✅ 2026-08-05 | Worst dip **11.80 V raw** at 0.45 m/s, sag **0.20 V** against a **0.71 V** margin — **3.5×**. Computer never faltered, uptime unbroken. Healthy pack only. §9.11 |

---

## D · Powered on, motors disarmed

| # | Confirm | How | Wrong ⇒ what breaks | Checked | Found |
|---|---|---|---|---|---|
| D1 | **`/dev/motordriver` is the ROSMaster, `/dev/lidar` is the A1** | Unplug one; check which symlink disappears | BRINGUP-2 was exactly this — the LiDAR was opening `/dev/motordriver` and reported a hardware timeout | — | |
| D2 | **The IMU reads level when the robot is level** | Put a spirit level on the chassis, then `ros2 run orbibot_localization measure_imu_noise -p duration:=60.0` — roll and pitch should be ≈ 0 | A tilt of 0.94° was measured 2026-08-04 and caused **83 %** of the yaw drift (LOC-1) | ◐ 2026-08-04 | roll **−0.935°** (right side up), pitch −0.018° |
| D2b | **Tilting the robot moves the right angle, in the right direction** | Hold it, then `python3 .claude/scripts/imu_sequence.py -d 75 -e level,roll+,roll-,pitch+,pitch-` and follow the cues. **Hold the front pointing AWAY from you** — facing you mirrors left and right | Verifies the whole convention chain at once: firmware axis order → driver → Madgwick → URDF `rpy` → ROS right-hand rule. A robot that never leaves level exercises none of it | ✅ 2026-08-04 | **Found a real bug.** Pairing was rotated 90° — the IMU is mounted 90° out and `imu_joint` said `rpy="0 0 0"`. Proven 3 ways, fixed, re-verified end to end. §9.9, DESC-2 |
| D3 | **`/scan` 0° is straight ahead** | Put a box 50 cm directly in front; the minimum range in `/scan` must be at angle ≈ 0 | Confirms A3 in software. A rotated LiDAR maps a consistent, wrong world | — | |
| D4 | **RViz pose matches the real robot's pose** | Open RViz, look at the model against the robot in front of you | Catches URDF errors that no test sees | — | |
| D5 | **Firmware version is what you think you flashed** | `ros2 service call /orbibot/get_firmware_version …` | "Upload succeeded" is not evidence the right binary is running | ✅ 2026-08-04 | `2.0` |

---

## E · Elevated on a stool, wheels free

**Ask before every one of these, and wait.** State that the robot must be
elevated and confirm it is, each session — not once.

| # | Confirm | How | Wrong ⇒ what breaks | Checked | Found |
|---|---|---|---|---|---|
| E1 | **Every wheel turns the right way for +Vx, +Vy, +ωz** | `.claude/scripts/motor.sh` — expected signs in `test-report.md` §6 | One inverted wheel makes the robot crab or spin instead of strafing | ✅ 2026-04-19 | all four patterns correct |
| E2 | **Encoder counts rise when the wheel is driven forward** | Same run; watch the tick signs | A flipped encoder makes odometry read backwards on that wheel only | ✅ 2026-04-19 | correct |
| E3 | **Encoder CPR is really 1320** | Mark the tyre, turn it **exactly one revolution by hand**, read the tick delta | The claim is 11 PPR × 30:1 × 4 — arithmetic, not a measurement. Every distance depends on it | — | |
| E4 | **Motors stop ~2 s after commands stop** | `test_safety.py` | Last line of defence if the network dies mid-drive | ✅ 2026-04-19 | 2.12 s |
| E5 | **M4 (back-right) really is the slow one** | `test_motor_max_speed.py`, then watch which physical wheel lags | FW-ISSUE-4 is unactionable until the slow motor has a physical identity | — | |
| E6 | **Cutting battery power stops everything at once** | Pull the battery connector mid-spin | This is the real emergency stop. It must be tested, not assumed | — | |

---

## F · On the ground, ≥ 2 m clear

**Unblocked as of 2026-08-05** — the Beelink is mounted (0.8 done) and the
robot has driven on the floor under its own battery (C4/P-3, §9.11). None of
F1–F5 has been taken yet; they need tape on the floor and a measured distance,
which P-3 did not provide. Worth doing together with Phase 0.9, since the
re-weigh happens on the same trip to the robot.

| # | Confirm | How | Gate | Checked | Found |
|---|---|---|---|---|---|
| F1 | **2 m commanded is 2 m travelled** | Tape on the floor, drive it, compare `/odom` | error < 3 %, both directions | — | |
| F2 | **10 × 360° comes back to the same heading** | Mark the floor and the chassis, count turns | accumulated error < 5° | — | |
| F3 | **Forward and backward at the same command travel the same distance** | Tape, both ways | agree within 5 % | — | |
| F4 | **Physical motion matches RViz** — forward, back, left, right, rotate | Drive each direction, watch RViz | exact agreement | ✅ before 2026-08-04 | matched; **re-check after remounting** |
| F5 | **Pull the wifi mid-drive and the robot stops** | Disconnect the network while driving | it stops. This is the test that matters | — | |
| F6 | **Yaw drift with the sensor level** | 10 min stationary after levelling | ~0.10 °/min expected, vs 0.547 measured tilted | — | |
| F7 | **Closed 4 m × 4 m loop** | Drive it, measure the gap | final error < 5 % of path length | — | |

---

## Already confirmed, and worth not re-litigating

| What | When | Evidence |
|---|---|---|
| ROSMaster board not rotated w.r.t. the chassis | 2026-08-04 | Operator, and independently `a_y` sign said "right side up" first |
| Physical motion matched RViz | before 2026-08-04 | Operator. **Invalidated by the board move — re-check (F4)** |
| Accelerometer scale, static | 2026-08-04 | `\|a\|/g = 1.0002`, 29 977 samples — `test-report.md` §9.7 |
| Wheel direction and mecanum signs, wheels-free | 2026-04-19 | `test-report.md` §6 |
| 2 s command timeout | 2026-04-19 | 2.12 s, `test-report.md` §7.1 |
| Adapter label voltage | 2026-08-03 | 19 V / 3.42 A, read off the label |

---

## Why a row here is worth more than a passing test

Three of this project's most expensive bugs were **not** software faults, and
none of them made anything fail:

- A test asked a human *"did the wheel spin forward?"* about a wheel that had
  never been commanded — the packet was rejected on a length check. The human
  said yes. FW-ISSUE-12.
- The accelerometer's inflated Z was compensated in software for four months.
  The compensation made the other two axes worse while making Z look right.
- The LiDAR was handed `/dev/motordriver` and reported a hardware timeout.
  A USB replug was requested, and proved nothing. BRINGUP-2.

Every one would have been caught in seconds by someone looking at the robot
with this list in hand.

## Related

[[test-index]] · [[testing-guide]] · [[roadmap]] Phase 0.8/0.9 ·
[[inventory]] · [[field-notes]] · `.claude/rules/robot-safety.md` ·
`src/orbibot_rosmaster_firmware/test-report.md`
