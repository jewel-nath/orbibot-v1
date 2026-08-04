# orbibot_description — Issue Tracker

**Package:** `orbibot_description` (URDF/Xacro, meshes, RViz)
**Last Updated:** 2026-08-04

---

## ✅ Fixed

### DESC-2: `imu_joint` claimed the IMU was aligned with the chassis. It is 90° out.
**Opened and fixed:** 2026-08-04 · **Severity:** MEDIUM
**File:** `urdf/orbibot.urdf.xacro:214`

```diff
-    <origin xyz="0.0 0.0 0.02" rpy="0 0 0"/>
+    <origin xyz="0.0 0.0 0.02" rpy="0 0 1.5707963"/>
```

The ICM-20948's axes are not aligned with the chassis: the sensor's **+X points
along the robot's left** (`base_link` +Y). The board is not rotated — the chip
on it is — which is why nothing looked wrong to the eye. Roll and pitch were
swapped everywhere downstream of the IMU for as long as this URDF has existed.

**Proven three independent ways** before the change was made, and verified
after. Full numbers in `test-report.md` §9.9:

| evidence | runs |
|---|---|
| Camera end tilted up/down moves **sensor roll**, not pitch | 3 separate holds, both directions |
| Frame is right-handed, so it is a **rotation** and not a mirrored axis order | 3 yaw rotations, clockwise and counter-clockwise |
| TF reports the new value | `base_link ← imu_link : yaw +90.00°` |
| A TF-aware consumer sees the right axis | camera up → `base_link` **pitch +8.32° = NOSE UP** |

The handedness test is the one that decided *where* the fix belonged. A
roll↔pitch swap could equally have been a reflection — X and Y exchanged without
a sign change — which no mounting can produce and which would have meant an
index bug in firmware or driver. Rotating clockwise gave gyro Z **−25.38** and
**−41.25 °/s**; counter-clockwise gave **+44.86**. Sign follows direction, so
the frame is right-handed, so it is a rotation, so the URDF is the right place.

**Impact before the fix: small, and about to stop being small.** `imu0_config`
fuses yaw and vyaw only, `imu0_relative: true` cancels a constant yaw offset,
and angular velocity about Z is unchanged by a Z-rotation — so the EKF's
arithmetic was unaffected. It would have started mattering the moment
`two_d_mode` was turned off, accelerometer fusion enabled, roll/pitch used for a
tilt or roll-over check, or anyone read `/imu/data_filtered` orientation
directly. RViz was wrong the whole time.

**Do not simplify this back to zero** because the board sits square in the
chassis. Verify with `.claude/scripts/imu_base_frame.py` instead — it resolves
the topic into `base_link` and prints both, so the difference is visible.

---

## ⚠️ Open

### DESC-1: the IMU has moved and the URDF has not
**Opened:** 2026-08-04 · **Severity:** LOW today, MEDIUM once the robot turns
**File:** `urdf/orbibot.urdf.xacro:214` — `imu_joint`

```xml
<origin xyz="0.0 0.0 0.02" rpy="0 0 1.5707963"/>
```

The **rotation** is now right (DESC-2). The **translation** is not: this places
the IMU exactly at the robot's centre, 2 cm up. On 2026-08-04 the
ROSMaster board — which carries the IMU — was **moved rearward** to make room
for the Beelink. Its orientation was not changed, so `rpy="0 0 0"` is still
right; the translation is not.

**What this does not affect, and why the 2026-08-04 IMU characterisation
(`test-report.md` §9.7) is unharmed:**

- Angular velocity is identical at every point of a rigid body, so the gyro
  does not care where it sits
- `imu0_config` fuses **yaw and vyaw only** — both translation-invariant
- The measurement was taken stationary, where a lever arm contributes nothing

**What it does affect, once the robot turns.** An IMU displaced by `d` from the
centre of rotation reads centripetal `ω²d` and tangential `αd` on top of
gravity. Madgwick has no way to know those are not gravity, so it reads them as
tilt:

| turn rate | lever arm | apparent tilt |
|---|---|---|
| 1.0 rad/s (~57 °/s) | 5 cm | 0.29° |
| 2.0 rad/s | 5 cm | 1.17° |
| 2.0 rad/s | 10 cm | 2.33° |

That feeds straight into the roll/pitch → yaw leak measured in
`localization-issue.md` LOC-1, where a **0.94°** static tilt already accounts
for 83 % of the heading drift. A turn-dependent tilt error of the same size is
worse, because it correlates with turning rather than averaging out.

**Fix:** measure the IMU's real offset from `base_link` when the robot is
reassembled and write it in. This belongs with **Phase 0.9** — the re-weigh and
footprint re-measure — because everything is being measured with a tape at that
point anyway. Do not estimate it now; the board is not in its final position.

**Also re-check while there:** `base_footprint → base_link`, the LiDAR and the
camera origins. Only the IMU is known to have moved, but the same session that
moves one board is the session that shifts the others.

---

## Related

`README.md` · `docs/packages/orbibot_description.md` ·
`src/orbibot_localization/localization-issue.md` LOC-1 ·
`src/orbibot_rosmaster_firmware/test-report.md` §9.7 ·
`docs/plan/roadmap.md` Phase 0.9
