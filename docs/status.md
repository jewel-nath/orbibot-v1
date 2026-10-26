---
title: "Backlog"
type: moc
tags:
  - moc
  - backlog
---

# Backlog

**This page does not hold findings.** They live beside the code they describe,
and a second copy here would be a second thing to keep true. What this page
holds is *where to look*, and the findings that belong to no single package.

## Per-package trackers

| Package | File | Entries |
|---|---|---|
| `orbibot_rosmaster_firmware` | `firmware-issue.md` | 9 |
| `orbibot_rosmaster_firmware` | `firmware-issue-deepdive.md` — static-analysis pass | 4 |
| `orbibot_webgui` | `webgui-issue.md` | 9 |
| `orbibot_hardware` | `hardware-issue.md` | 6 |
| `orbibot_agent` | `agent-issues.md` | 3 |

Measured results are separate from findings: firmware numbers go in
`test-report.md`, in dated sections.

## Cross-cutting — belongs to no package

### CC-1 · Four unarbitrated `/cmd_vel` publishers · **HIGH**

`orbibot_hardware` subscribes to `/cmd_vel`. Four things publish to it, and
nothing decides between them:

| Publisher | Where |
|---|---|
| Web dashboard | `orbibot_webgui` frontend, via rosbridge |
| AI agent | `orbibot_agent/core/ros_bridge/motion.py` |
| Gamepad teleop | `orbibot_teleop/controller.py` (dormant, but wired) |
| Nav2 | `collision_monitor` output |

There is **no `twist_mux` anywhere in the workspace** — verified 2026-08-03 by
grep across `src/`. Last writer wins. A Nav2 goal and a dashboard joystick can
fight mid-drive, and nothing has priority or a timeout.

Design and the fix: [[command-pipeline]]. Gate for Phase 2 in [[roadmap]].

### CC-2 · Accel X/Y scale unconfirmed under real acceleration · **MEDIUM**

The Z-axis self-test fix (`test-report.md` §9.4) is verified static:
`|a| = 9.802 m/s²`, ratio to g **0.9995**. But X and Y read ~0 on a static
robot either way, so the corrected scale on those two axes — the ones a ground
robot actually accelerates along — has not been shown. Needs a known
acceleration with the robot **on the ground**.

### CC-3 · Every pre-2026-08 localisation conclusion is suspect · **MEDIUM**

Two separate faults were feeding the estimator bad data for months: the
accelerometer was inflated on Z, and the raw-IMU path was silently dropped by a
length check whenever firmware and driver were out of step. Any tuning result,
drift figure or EKF covariance recorded before 2026-08-03 was measured through
that. Re-measure rather than trust — see [[roadmap]] Phase 1.

### CC-4 · `orbibot_localization/README.md` still describes the magnetometer · **LOW**

It says the Madgwick stage "fuses raw IMU + magnetometer → drift-free
orientation". `madgwick_params.yaml` has `use_mag: false`, and magnetometer
support was deleted across firmware, driver and msgs on 2026-04-28. The README
was not updated with it.

## Related

[[docs/README|Docs home]] · [[roadmap]] · [[packages-moc]] · [[command-pipeline]]
