# Firmware Deep-Dive Audit — Open Issues

**Audit started:** 2026-04-28 by Claude (Opus 4.7) under Jewel Nath's direction.
**Scope:** Re-grepped the entire firmware tree against six dimensions
(concurrency, numerical/control, protocol contract, boundary/overflow, power /
safety paths, build hygiene). Skips items already in `firmware-issue.md` or
`firmware-changelog.md`.

> Companion of `firmware-issue.md`. Severity-sorted; each finding states
> **file:line**, **what is wrong**, **why it matters** (concrete consequence),
> and **fix**. `[VERIFIED-LIVE]` = reproduced on hardware; `[STATIC-ONLY]` =
> code-walk only.
>
> **Closed items** are moved to `firmware-changelog.md`, not retained here.

---

## 🟡 LOW

### DD-7: `vy` sanity-check spec drift between firmware and ROS 2 frame convention [STATIC-ONLY]

**Files:** `src/communication/protocol.c` line 451–470,
`src/control/mecanum_kinematics.c` line 31–46.

**Severity:** LOW · *no actual bug, comment hygiene only*

The `Vy double negation` from the 2026-03-25 changelog has been correctly
removed. Both sides now use ROS frame `+Y = left`. However, the
firmware-side `protocol_handle_motion()` still has multi-line comments
explaining why no inversion is needed (lines 469–470, plus the Vy
convention block in `mecanum_inverse_kinematics`). These are documentation
of an absent transformation — accurate, but a future reader may flip the
sign "to fix it" if they don't read the test report.

**Suggested action:** add a one-line `// FW-BUG-2 fix history: see
firmware-changelog.md` near the convention block instead of three
paragraphs of justification. Optional cleanup.

---

## ℹ️ INFO

### DD-8: `MAX_LINEAR_SPEED_MM` cast from float at compile time [STATIC-ONLY]

**File:** `src/communication/protocol.c` lines 455–456

```c
static const int16_t MAX_LINEAR_SPEED_MM = (int16_t)(MAX_LINEAR_VELOCITY_MPS * 1000.0f);
```

`MAX_LINEAR_VELOCITY_MPS = 1.0f` so this resolves to 1000 at compile time
and is fine. `MAX_ANGULAR_VELOCITY_RPS = 2.0f` resolves to 2000 — the
clamp `vz_raw > MAX_ANGULAR_SPEED_MRAD = 2000` then refuses to ever
command rotation faster than 2 rad/s. Confirmed intentional vs the YAML
(`max_angular_velocity: 2.0`). No bug, just cross-referencing.

---

### DD-9: USART error counter is set but never reported to the host [STATIC-ONLY]

**File:** `src/hal/hal_usart.c` lines 30, 245–259.

`usart_errors` accumulates `ORE | FE | NE` flag bits in the ISR but is
exposed only via `hal_usart_get_errors()` — which has *zero callers* in
the firmware (verified by grep). Same situation as the `g_rx_drop_count`
and `g_unknown_cmd_count` counters mentioned in `firmware-issue.md` →
"diagnostics packet" improvement idea. Worth bundling those four counters
into one `0x?? REPORT_DIAG` packet for ROS 2-side visibility, especially
now that the DD-1 fix routes truncated-packet drops into
`g_unknown_cmd_count`.

---

### DD-10: `vApplicationStackOverflowHook` halts with interrupts disabled [STATIC-ONLY]

**File:** `src/main.c` lines 526–534.

When a stack canary fires, the hook prints to USART1 directly and spins
forever with `__disable_irq()`. Watchdog (IWDG) keeps running because
it's clock-independent — MCU resets after 5 s. No ROS 2-side signal that
"this was an overflow, not a generic hang" — the operator sees a reset
and loses the printed `[FATAL] Stack overflow: TaskName` because the
serial line is busy with auto-report packets at the moment of the fault.

**Mitigation:** the hook would be more useful if it pushed a magic
sentinel into a known RAM location (e.g., backup register `BKP_DR1`)
before halting; on the next boot, `main` checks the sentinel and, if
present, sends a `0x?? REPORT_LAST_FAULT` packet identifying the
crashed task. Would need 2 bytes of backup register and a 2-line
`HardFault_Handler` shadow. INFO only — the current behaviour is safe;
an operator with a serial monitor will see the message most of the time.

---

## ✅ Things I rechecked and they're fine

| Subsystem | Hot spot | Verdict |
|-----------|----------|---------|
| `g_rx_*` (ISR ↔ comm) | RX state machine, double-buffer | OK — index/state writes serialised, bytes go to staging until LEN known |
| `target_vel`/`measured_vel` (ctrl ↔ comm) | float fields | OK — critical-section writes on both sides |
| `g_imu_data` (imu → comm) | 40-byte struct | OK — only reader is lower-priority comm task; can't tear |
| `g_roll/pitch/yaw` (imu → control + comm) | 3 floats | OK — all readers/writers in critical sections |
| `firmware_odom` (control ↔ comm) | 6 floats | OK — `control_get_firmware_odometry` enters critical section |
| `pid_motor[]` gains (proto-handler ↔ control) | 4× pid struct | OK — `control_set_motor_pid` critical-sections the entire update |
| Mecanum sign vector | `mecanum_inverse/forward_kinematics` | OK — both functions are exact inverses by hand-trace; matches live test report §6 |
| PID anti-windup | `pid_calculate_incremental` | OK — clamp + same-direction-saturated check correctly stops integration only in the saturating direction |
| Odometry RK2 normalisation | `odometry_update` | OK — `theta` increments first, `fmodf(theta, 2π)` then ±π correction; delta-x/y already projected with `mid_theta` so order is right |
| Encoder 16-bit modular subtract | `hal_timer_read_encoder_delta` | OK — 73 ticks/call worst case ≪ 32768 |
| Odometry int32 packet | `protocol_send_odometry_data` | OK — x_mm wraps after ~24 days of sustained 1 m/s |
| IMU range × 1000 → int16 | gyro ±500 dps, accel ±2 g | OK — max 8 727 / 19 613 milli-units, both < 32 767 |
| Battery thresholds vs YAML | `orbibot_config.h` ↔ `hardware_params.yaml` | OK — 11.0 / 10.5 V in both |
| Velocity limits vs YAML | same | OK — 1.0 m/s linear, 2.0 rad/s angular |
| Command timeout vs YAML | `COMMAND_TIMEOUT_MS = 2000` ↔ `cmd_timeout: 2.0` | OK |
| Pre-scheduler watchdog feed | `main()` line 446 | OK — handles fast-LSI hardware (FW-BUG-3 history confirms) |
| Watchdog gating | `task_monitoring` only feeds when *all 4* alive counters advance | OK — including initial-iteration-after-boot edge case |
| Saturation guards | `g_rx_drop_count++` saturates at `UINT32_MAX`, `protocol_send_motion_data` saturates voltage | OK |
| Per-motor steady-state speed (FW-ISSUE-4 baseline) | M1–M4 at 1.0 m/s commanded | OK — 0.1 % inter-motor variation; M4 stiction is transient only (see `test-report.md §9.2`) |

---

## 🧹 Documentation hygiene

- **`firmware-issue.md::FW-ISSUE-4`** ("`MAX_WHEEL_SPEED_MMS = 3500`
  too loose") now has a measured baseline: `test-report.md §9.2` shows
  worst-case combined wheel speed at firmware velocity caps is ~1.94 m/s.
  Recommendation: tighten `MAX_WHEEL_SPEED_MMS` to 2200 (10 % margin).

---

## See also

- `firmware-issue.md` — earlier open issues
- `firmware-changelog.md` — fixed items (verify before re-investigating)
- `test-report.md` — live verification snapshots, §9 is this audit's tests
