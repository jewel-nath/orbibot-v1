---
title: "Inherited Values"
type: plan
tags:
  - plan
  - tuning
  - beelink
---

# Values inherited from the Raspberry Pi

Every tuning number in this repo that was chosen to fit a **Raspberry Pi 5**,
and is therefore no longer a measured number. The Pi was replaced on 2026-08-03
by a **Beelink SER5 Pro** — Ryzen 7 PRO 5800H, 8C/16T, 11.6 GiB, x86_64.

This file exists because these are easy to miss: they look like considered
engineering choices, and several carry confident comments explaining a
constraint that no longer exists.

> **The rule is not "raise everything".** The Pi-era mistake was lowering values
> without measuring. Raising them without measuring is the same mistake pointed
> the other way. Each row below names *what to derive the new value from*.
> — [[roadmap]] Principle 5.

**Two limits are not CPU and do not move with the new machine:**

- **`/scan` is 8.0 Hz** — the A1's motor speed, not a setting. Measured
  2026-08-04; SENS-1 is resolved, and the docs that said 10 Hz were quoting the
  datasheet maximum. A costmap updating faster than 8 Hz reprocesses the same
  scan, so derive costmap and controller rates from this number.
- **The RealSense link is 480 Mbps** (SENS-2). Camera resolution, depth filters
  and pointcloud all stay blocked until that is 5000.

---

## Done

| Package | Parameter | Was | Now | Derived from |
|---|---|---|---|---|
| `orbibot_localization` | `ekf frequency` | 25.0 Hz | **50.0 Hz** | Both fused inputs run at 50 Hz (`/imu/data_raw` 49.99, `/joint_states` 49.97). Measured after: `/odometry/filtered` 49.999 Hz, ekf_node **1.6 % of one core**, RSS 38.7 MB, machine 98.7 % idle — 2026-08-04 |

---

## Open

### `orbibot_sensors` — blocked on SENS-2 (480 Mbps link)

| Parameter | Current | Origin | Derive from |
|---|---|---|---|
| `color_width/height/fps` | 424×240 @ 15 | "reduced for RPi" | USB 3 link + Phase 3 CPU budget |
| `depth_width/height/fps` | 424×240 @ 15 | "reduced for RPi" | as above; depth feeds Phase 6.6 costmap |
| `align_depth.enable` | `false` | "reduced for RPi" | needed for depth→costmap projection |
| `pointcloud.enable` | `false` | "reduced for RPi" | needed only if a voxel/STVL layer uses it |
| `spatial_filter.enable` | `false` | "disabled for RPi" | depth quality vs CPU, measured |
| `temporal_filter.enable` | `false` | "disabled for RPi" | as above |

### `orbibot_slam` — Phase 5

| Parameter | Current | Origin | Derive from |
|---|---|---|---|
| `map_update_interval` | 5.0 s | was 2.0, "reduces CPU load significantly" | mapping run on the new machine |
| `transform_publish_period` | 0.05 | was 0.02 | TF consumers' needs |
| `tf_buffer_duration` | 10.0 s | was 30.0, "saves memory" | 11.6 GiB — memory is not scarce |
| `stack_size_to_use` | 20 MB | was 40 MB | as above |
| `minimum_time_interval` | 0.3 s | fitted against an assumed scan rate | the **measured** scan rate (SENS-1) |
| `enable_interactive_mode` | `false` | "saves memory" | whether it is wanted, not whether it fits |

### `orbibot_navigation` — Phase 6

| Parameter | Current | Origin | Derive from |
|---|---|---|---|
| `controller_frequency` | 5.0 Hz | "cut to fit a Raspberry Pi 5" | scan rate and Phase 0.11 CPU baseline |
| MPPI `batch_size` | 500 | "cut for Raspberry Pi 5 CPU load" | trajectory quality vs measured CPU — the clearest single win available |
| MPPI `time_steps` / `model_dt` | 15 / 0.2 | same era | horizon needed at the real max speed |
| `transform_tolerance` | 1.0 s | "relaxed for RPi — prevents extrapolation into future errors" | a tolerance this loose hides real TF lateness |
| local costmap `update_frequency` / `publish_frequency` | 10.0 / 10.0 | comment claims "match controller frequency (10 Hz)" — **the controller is 5.0, so the comment is already wrong** | scan rate |
| global costmap `update_frequency` / `publish_frequency` | 2.0 / 1.0 | Pi era | map size and planner rate |
| `max_accel` | [0.6, 0.6, 2.0] | "reduced for smoother motion" | Phase 1 measured limits **under the mounted mass** |

---

## How to work through this

1. Do not change a row without a measurement to justify it, and write the
   measurement into the config comment beside the value — with the date and the
   robot's state. A number in a commit message gets lost; a number beside the
   value gets read.
2. Record the before *and* after. "50 Hz costs 1.6 % of a core" is the sentence
   that stops someone re-lowering it next year.
3. Phase 0.11 — **CPU baseline while driving** — is the measuring stick for
   every CPU-bound row here, and it has not been taken yet.

## Related

[[roadmap]] · [[baseline-results]] · [[next-session-prompt]] ·
`src/orbibot_sensors/sensors-issue.md` · [[dashboard-design]]
