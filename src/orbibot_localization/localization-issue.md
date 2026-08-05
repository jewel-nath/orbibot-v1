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

> ### ⚠️ The paragraph this replaced was wrong, and was committed as fact
>
> It read *"Tilt direction — confirmed, and the axes are fine"*, and closed the
> axis question on two things agreeing: the sensor said `roll −0.935°`, and the
> operator said the right side looked high.
>
> They agreed by coincidence. The operator's **first** description had been
> *"the rear is raised"* — a pitch — and the second was hedged (*"it seems"*).
> Taking a hedged observation as independent confirmation of a measurement, and
> then closing an open question with it, is the mistake. **The axes were not
> fine.** See `test-report.md` §9.9 and DESC-2.

**Tilt direction, and what it actually was.** The IMU is mounted **rotated 90°
about Z**: sensor +X points along the robot's left. Proven three ways, in
`test-report.md` §9.9 — three separate camera-up/down holds, three yaw rotations
in both directions to establish handedness, and an end-to-end check after the
fix. `imu_joint` now carries `rpy="0 0 1.5707963"`.

Translating this issue's own numbers through that rotation:

| sensor reads | physically |
|---|---|
| roll −0.935° | **rear raised 0.94°** |
| pitch −0.018° | no side tilt |

Which is what the operator said before anything was measured.

**The drift analysis below is unaffected.** It was computed entirely in the
sensor frame and is self-consistent there; only the labels move. The leaking
term is the **sensor Y** gyro bias (−0.457 °/s) — the robot's *roll* axis —
leaking through a rear-up *pitch*. The 0.47 % agreement, the 5.6×, and the
remedy all stand.

**That reasoning has expired.** It said levelling belongs in Phase 0.8 because
the board would come off anyway when the Beelink, converter and fuse were
mounted. Phase 0.8 was already done — long before, per the operator on
2026-08-05 — so the board did not come off and nothing was levelled.

Levelling now means unscrewing a board that is currently working, which is not
free. **Before touching it, run the 180° test**: measure the tilt, rotate the
robot 180° on the same floor, measure again. A tilt that follows the robot is
in the mounting; a tilt that stays put is in the floor, and unscrewing anything
would be chasing the room.

**Also left open by the board being moved rearward:** `imu_joint`'s *translation*
is still `xyz="0 0 0.02"`, the robot's centre, and the IMU is no longer there —
`description-issue.md` DESC-1. No effect on anything measured here (angular
velocity is position-independent, `imu0_config` fuses yaw and vyaw only, and
every run was stationary), but it matters during turns, where a lever arm `d`
adds `ω²d` that Madgwick reads as tilt: 0.29° of apparent tilt at 1 rad/s with
d = 5 cm.

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
