# orbibot_description — Issue Tracker

**Package:** `orbibot_description` (URDF/Xacro, meshes, RViz)
**Last Updated:** 2026-08-04

---

## ⚠️ Open

### DESC-1: the IMU has moved and the URDF has not
**Opened:** 2026-08-04 · **Severity:** LOW today, MEDIUM once the robot turns
**File:** `urdf/orbibot.urdf.xacro:214` — `imu_joint`

```xml
<origin xyz="0.0 0.0 0.02" rpy="0 0 0"/>
```

That places the IMU exactly at the robot's centre, 2 cm up. On 2026-08-04 the
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
