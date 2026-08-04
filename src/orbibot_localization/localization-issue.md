# orbibot_localization — Issue Tracker

**Package:** `orbibot_localization` (Madgwick + EKF → `odom → base_footprint`)
**Last Updated:** 2026-08-04

---

## ⚠️ Open

### LOC-1: yaw drift is 5.6× worse than the gyro deserves — the sensor is not level
**Opened:** 2026-08-04 · **Severity:** MEDIUM — it is the heading budget
**Where:** hardware mounting, not code. `madgwick_params.yaml` `zeta` is the
software half of the answer.

Measured over 10 minutes, robot elevated on a stool, motors disabled, 29 977
samples — full numbers in `test-report.md` §9.7:

| | °/min |
|---|---|
| **Measured yaw drift** | **+0.547** (33 °/hour) |
| Predicted from gyro Z bias alone | +0.097 (5.8 °/hour) |

The gap is not noise and not a gyro fault. Gravity shows the sensor tilted
**roll −0.935°, pitch −0.018°**, and Euler kinematics leak the other gyro axes
into yaw through exactly that tilt:

```
ψ̇ = (ω_y·sin φ + ω_z·cos φ) / cos θ  =  +0.544 °/min
```

against +0.547 measured — **0.47 % error**. So **83 % of the heading drift is
gyro Y bias (−0.457 °/s) projected through a 0.94° mounting tilt**, on an axis
that no part of the pipeline watches.

This matters more here than it would on most robots: the magnetometer was
removed on 2026-04-28 because indoor iron and motor currents made heading
worse. Nothing observes heading now, so every bit of gyro bias integrates
forever until SLAM or AMCL corrects `map → odom`.

**Two independent fixes, and both are worth doing:**

1. **Level the sensor** (hardware). Costs nothing at runtime and removes the
   leak at its source. Drift should fall to ~0.10 °/min.
2. **Raise Madgwick `zeta` above 0.0** (software). `zeta` estimates gyro bias
   from the accelerometer, which observes **roll and pitch** — precisely the X
   and Y axes whose bias is leaking. The parameter's current comment says zeta
   "becomes less effective" with `use_mag: false`; that is true for *yaw* bias,
   and the measurement shows yaw bias is the negligible term (0.0016 °/s)
   while X/Y bias is 90–280× larger and **is** observable. The comment is
   steering people away from the parameter that would help most.

   Do not simply raise it — measure. Re-run the 10-minute characterisation at
   `zeta: 0.0`, then at a candidate value, and compare drift. The tool prints
   the bias prediction beside the measured drift for exactly this comparison.

**Tilt direction — confirmed, and the axes are fine.** For a moment this looked
like it might be an axis bug: the measurement says *roll*, and the board had
been described as having its rear raised, which would be *pitch*. It is not a
bug. The operator confirmed the board was **moved backward** to make room for
the mini PC with **its direction unchanged**, and that the **right side sits
slightly high**.

The sensor had already said so, before anyone looked:

```
a_y = −0.160 m/s²  →  roll = −0.935°
negative roll about +X rotates +Y (left) toward −Z  →  left side down, RIGHT SIDE UP
```

Two independent observations agreeing on which side is up is also a check on
the whole convention chain — firmware axes, driver, URDF, ROS sign convention.
`imu_joint` at `rpy="0 0 0"` stands, and physical motion still matches RViz.

**Levelling is worth about 5.6× on drift, and it should happen during Phase
0.8, not before.** The board will be unbolted anyway when the Beelink,
converter and fuse go on. Adjusting it now means adjusting it twice.

**Left open by the same change: the IMU is no longer where the URDF says.**
`imu_joint` is fixed at `xyz="0.0 0.0 0.02"` — the robot's centre — and the
board has since moved rearward. See `orbibot_description/description-issue.md`
DESC-1. It has **no effect on anything measured here**: angular velocity is
identical everywhere on a rigid body, and `imu0_config` fuses yaw and vyaw
only, both translation-invariant. It starts to matter during turns, where a
lever arm `d` adds centripetal acceleration `ω²d` that Madgwick reads as tilt —
0.29° of apparent pitch at 1 rad/s with d = 5 cm — feeding the exact
roll/pitch → yaw leak described above.

**Blocks:** Phase 4.2 (`gain`/`zeta` tuning) should not be finalised against a
drift figure taken with the sensor tilted.

---

### LOC-2: `orientation_stddev` is an adjective, not a measurement
**Opened:** 2026-08-04 · **Severity:** LOW
**File:** `config/madgwick_params.yaml`

`orientation_stddev: 0.05` carries the comment *"~3° std dev — realistic for
ICM-20948 + Madgwick"*. It is one of only **two** numbers that reach the EKF
from the IMU path (the other is `gyro_covariance_z`), because `imu0_config`
fuses yaw and vyaw only. "Realistic" is not a measurement, and this one is load
bearing.

Derive it from the spread of `/imu/data_filtered` yaw about its drift line over
a stationary run — the residual after removing the linear trend is the
orientation noise the EKF should expect. The 10-minute capture already exists;
the tool needs to report the detrended residual.

---

## ✅ Resolved

### CC-4 — the README's magnetometer claim
Closed 2026-08-04. Already fixed in `bf8d74f`; the backlog entry had simply
never been closed. See `docs/moc/backlog-moc.md`.

### EKF rate was a Raspberry Pi compromise
`frequency: 25.0` → **50.0**, 2026-08-04. Both fused inputs run at 50 Hz;
measured after: `/odometry/filtered` 50.00 Hz, `ekf_node` 1.6 % of one core.
See `docs/plan/inherited-values.md`.

---

## Related

`README.md` · `localization-changelog.md` ·
`src/orbibot_rosmaster_firmware/test-report.md` §9.7 ·
`docs/packages/orbibot_localization.md` · `docs/plan/roadmap.md` Phase 4
