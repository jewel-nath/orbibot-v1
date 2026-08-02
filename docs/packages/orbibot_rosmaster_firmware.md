---
title: "orbibot_rosmaster_firmware"
type: package
tags:
  - package
  - firmware
---

# orbibot_rosmaster_firmware

Custom firmware for the Yahboom ROSMaster V3.0 (STM32F103RCT6), replacing
Yahboom's closed-source original. Everything with a deadline lives here.

> **The API reference is `src/orbibot_rosmaster_firmware/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

Motor PID at 100 Hz · quadrature encoders · ICM-20948 IMU · wheel odometry ·
the binary serial protocol · flash-stored settings · the 2 s command timeout.

**Not a colcon package.** It carries a `COLCON_IGNORE` and is built by
PlatformIO:

```bash
cd src/orbibot_rosmaster_firmware
~/.platformio/penv/bin/pio run                  # build
~/.platformio/penv/bin/pio run --target upload  # needs BOOT0 — ask the operator
~/.platformio/penv/bin/pio device monitor       # 115200
```

The toolchain is pinned in `platformio.ini` so the Pi 5 can build it; the
version range `ststm32` asks for predates the `linux_aarch64` build.

## Look first

| File | For |
|---|---|
| `firmware-architecture.md` | How the tasks and drivers fit together |
| `include/protocol.h` | The wire contract — the single authority |
| `test-report.md` | What has been verified live, in dated sections |
| `firmware-issue.md` | What is open |
| `firmware-issue-deepdive.md` | The static-analysis pass |
| `tests/run_all_tests.py` | Serial test suite; no ROS needed |

## Open

- `MAX_WHEEL_SPEED_MMS` is theoretical, not measured; M4 runs 12–15 % slower
  than M1–M3 (FW-ISSUE-4) — roadmap 1.7
- IMU variance is computed but never sent to ROS 2 (FW-ISSUE-7)
- Three files are large and mix concerns — `protocol.c`, `imu_driver.c`,
  `task_control.c` (TD-1..3, deferred)
- Accel X/Y scale unconfirmed under real acceleration — [[backlog-moc]] CC-2

## Recently closed

The Z-axis self-test that had been inflating `az` since March — and the
compensation factor that hid it. `test-report.md` §9.4.

## Related

[[packages-moc]] · [[orbibot_hardware]] · [[rosmaster-board]] ·
[[firmware-architecture]] · [[firmware-moc]]
