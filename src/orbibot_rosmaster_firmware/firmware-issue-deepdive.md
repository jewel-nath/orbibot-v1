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

## 🟠 MEDIUM

### DD-2: `BUZZER_OFF` from a host BEEP command can silence the critical-battery alarm [STATIC-ONLY]

**Files:** `src/communication/protocol.c` lines 376–394 (`case FUNC_BEEP`),
`src/tasks/task_monitoring.c` lines 96–112 (critical branch).

**Severity:** MEDIUM (safety-adjacent)

**What is wrong:**
When battery falls below `BATTERY_VOLTAGE_CRITICAL` (10.5 V), MonitorTask
calls `BUZZER_ON()` for a *continuous* alarm and locks out motors. Nothing
remembers "we are in CRITICAL state" inside the buzzer subsystem. If the
host (ROS 2 or operator) sends a `FUNC_BEEP` with `on_time = 0`, the
handler unconditionally calls `BUZZER_OFF()`, silencing the critical
alarm even though the lockout is still active.

**Why it matters:**
Operator depends on the audible alarm to know the robot has stopped due
to dangerously low voltage. A stray `set_beep(0)` from any tool sharing
the link silences the alarm; the user sees a robot that "won't move" but
no audible cue that the cause is empty battery. Lockout itself remains in
place (good — safety not lost), but discoverability is.

The ROS 2 driver has no current code path that sends `set_beep(0)` while
in CRITICAL, but the `/orbibot/beep` topic is publicly published — an
end-user `ros2 topic pub` of `0` will silence the alarm.

**Fix:** In `case FUNC_BEEP:`, refuse to turn the buzzer off while
`control_get_battery_lockout()` is active:
```c
if (on_time == 0)
{
    if (!control_get_battery_lockout())  // critical alarm has priority
        BUZZER_OFF();
}
```

---

### DD-3: `g_double_beep_state` + `g_double_beep_phase_tick` writes are not atomic [STATIC-ONLY]

**File:** `src/communication/protocol.c` line 801

**Severity:** MEDIUM (cosmetic safety-adjacent)

**What is wrong:**
```c
void protocol_start_double_beep(void)
{
    g_double_beep_state = DOUBLE_BEEP_ON1;        // ← (A)
    g_double_beep_phase_tick = xTaskGetTickCount();
    BUZZER_ON();
}
```
Called from `task_monitoring` (priority 5). `protocol_update_buzzer()`
runs in `task_communication` (priority 7) and reads the *pair*
`(g_double_beep_state, g_double_beep_phase_tick)` to advance the state
machine. If CommTask preempts MonitorTask between line (A) and the
next line, CommTask sees `state=ON1` with the *old* `phase_tick` from
the previous double-beep — possibly seconds ago — `elapsed_ms ≥ 200`
fires immediately, transitions to `OFF1`, calls `BUZZER_OFF()`. Net
visible behaviour: at the moment battery first crosses the LOW
threshold, the user hears a click instead of a 200 ms double-beep.

**Why it matters:**
The first low-battery warning is precisely the one you want to be
audible. After the state machine advances past the glitch, subsequent
double-beeps behave correctly. So the failure is at the most-important
moment.

**Fix:**
```c
void protocol_start_double_beep(void)
{
    taskENTER_CRITICAL();
    g_double_beep_state = DOUBLE_BEEP_ON1;
    g_double_beep_phase_tick = xTaskGetTickCount();
    taskEXIT_CRITICAL();
    BUZZER_ON();
}
```

---

### DD-4: ROS 2 driver's `forever=True` on auto-report is silently dropped by firmware [STATIC-ONLY]

**Files:**
- ROS 2: `src/orbibot_hardware/orbibot_hardware/rosmaster_driver.py` line 297 (`set_auto_report_state`).
- Firmware: `src/communication/protocol.c` line 427 (`protocol_handle_auto_report`).

**Severity:** MEDIUM (feature gap → silent regression risk)

**What is wrong:**
The ROS 2 driver sends a 2-byte `[state, save]` payload where
`save = 0x5F` if the caller passed `forever=True`. Firmware reads only
`data[0]` and discards `data[1]` — so the persist-to-flash semantics
that the driver advertises don't actually run.

**Why it matters:**
A future user who wants the robot to auto-stream sensor data on power-up
without an explicit ROS 2 enable command cannot get there from here.
Today the ROS 2 hardware node always re-issues `enable_auto_report(True)`
on connect, so nobody notices — but if anyone refactors that out, sensor
streams will silently stop streaming on boot. Worth either implementing
or removing the `forever` parameter from the Python side.

**Fix (one of two):**
1. Honour `data[1]`: if `data[1] == SAVE_VERIFY`, save a "default
   auto-report=on" flag in `flash_storage` and have `protocol_init()`
   set `g_auto_report_enabled` from the flash flag at boot. Adds one
   `bool` to the flash schema.
2. Drop the parameter on the ROS 2 side and document that auto-report
   is always commanded explicitly by the host.

Recommend option 2 — auto-report on boot has no actual user benefit
on this robot since the host always controls the connection.

---

### DD-11: `FUNC_SET_MAG_CAL` writes flash unconditionally — no `SAVE_VERIFY` gate [STATIC-ONLY]

**File:** `src/communication/protocol.c` line 707

**Severity:** MEDIUM (flash wear + design inconsistency)

**What is wrong:**
```c
void protocol_handle_set_mag_cal(const uint8_t *data)
{
    /* parse 6 bytes into mag_calibration_t cal */
    imu_set_mag_calibration(&cal);
    flash_storage_save();   // ← always, no opt-out
}
```
`protocol_handle_set_motor_pid()` and `protocol_handle_set_yaw_pid()`
both gate the flash write behind `if (state == SAVE_VERIFY)` — so a
caller can update gains live without persisting. `protocol_handle_set_mag_cal()`
has no equivalent gate. Every magnetometer-calibration command from the
host therefore consumes one flash erase cycle.

**Why it matters:**
1. **Flash wear** — STM32F103 flash has ~10 000 erase cycles per page.
   A calibration tool that streams updates during a "rotate the robot
   for 30 s" routine could plausibly send 30+ updates and burn through
   0.3 % of the flash budget per session. Not catastrophic, but
   completely avoidable.
2. **Inconsistency** — the firmware's three "set persistent value"
   handlers (motor PID, yaw PID, mag cal) split 2-1 on the SAVE_VERIFY
   gate. Picking up the same convention everywhere makes the contract
   easier to remember on both sides.
3. **Test cost** — a RAM-only round-trip test cannot exist today.
   `tests/test-report.md §9.3` deferred this as a Phase-3 follow-up.

**Fix:**
1. Extend the wire format from 6 bytes to 7: `[ox_lo][ox_hi][oy_lo][oy_hi][oz_lo][oz_hi][state]`.
2. Update `protocol_min_rx_len(FUNC_SET_MAG_CAL)` from 11 to 12.
3. Match the PID handler:
   ```c
   if (data[6] == SAVE_VERIFY) flash_storage_save();
   ```
4. Update `rosmaster_driver.set_mag_calibration()` to send the trailing
   state byte (`0x5F` when caller passes `save=True`, else `0x00`).

---

## 🟡 LOW

### DD-5: `mag_cal` (52-byte struct) read/write race [STATIC-ONLY]

**File:** `src/drivers/imu_driver.c` lines 707, 567 (writer / reader).

**Severity:** LOW (one bad mag-corrected sample per torn read; EKF tolerates).

**What is wrong:**
`imu_set_mag_calibration()` is called from `task_communication` (priority
7) on `FUNC_SET_MAG_CAL` and copies the entire 52-byte struct without a
critical section. `imu_read_both()` runs in `task_imu` (priority 8) at
50 Hz and reads the same fields. Higher-priority `task_imu` can preempt
`task_communication` mid-copy, observing an inconsistent snapshot of
hard-iron offsets and soft-iron matrix.

**Why it matters:**
Mag calibration is set rarely (once per session, manually via a
calibration tool), so the chance of a torn read coinciding with a
calibration update is small. When it does happen, exactly one IMU
sample at 50 Hz contains a mixed-old/new calibration, producing a yaw
glitch that the gyro-dominated complementary filter (α=0.98) attenuates
heavily. Net visible effect: brief sub-degree yaw twitch right at the
moment the calibration command is received.

**Fix:** Wrap `mag_cal = *cal;` in `taskENTER_CRITICAL()/taskEXIT_CRITICAL()`
inside `imu_set_mag_calibration()`. Also wrap the `mag_cal.*` reads in
`imu_read_both()`'s calibration block. Cheap.

---

### DD-6: Mag yaw blending sign convention untested on this hardware [STATIC-ONLY]

**File:** `src/tasks/task_imu.c` line 178

**Severity:** LOW (impacts long-duration heading stability only)

**What is wrong:**
```c
float mag_yaw = atan2f(-imu_data.mag_y, imu_data.mag_x);
```
The complementary filter blends `mag_yaw` into `gyro_yaw` at α=0.02 weight.
The sign of the `mag_y` argument depends on the chip's mounting
orientation on the ROSMaster V3.0 board *relative to the robot body*. If
the chip's +Y points away from robot's +Y (left), the `-mag_y` is
correct. If +Y points toward robot's +Y, the formula should be
`atan2f(mag_y, mag_x)`.

**Why it matters:**
A wrong sign means the magnetometer correction *opposes* the gyro
integration over long horizons. Short-term you wouldn't notice (gyro
dominates); after several minutes of operation yaw can drift several
degrees more than gyro-only would.

**Fix:** Rotate robot CCW by ~360° on the ground (not on blocks — the
chip needs to physically rotate) and check whether the
`/imu/data_filtered` yaw value tracks the actual rotation in the same
direction. If it tracks opposite, flip the `-imu_data.mag_y` sign.

---

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
| AK09916 WHO_AM_I check | `mag_init()` line 302 | OK — *contradicts* `firmware-issue.md::FW-ISSUE-6` which calls this missing. **`firmware-issue.md` is stale** — see cleanup item below. |
| Saturation guards | `g_rx_drop_count++` saturates at `UINT32_MAX`, `protocol_send_motion_data` saturates voltage | OK |
| Per-motor steady-state speed (FW-ISSUE-4 baseline) | M1–M4 at 1.0 m/s commanded | OK — 0.1 % inter-motor variation; M4 stiction is transient only (see `test-report.md §9.2`) |

---

## 🧹 Documentation hygiene

- **`firmware-issue.md::FW-ISSUE-6` is stale.** `mag_init()` already
  reads back `WIA2` and rejects on mismatch (see `imu_driver.c` line
  302–311 plus the `BOOT_PRINTF` warning). Move FW-ISSUE-6 to the
  changelog under a future "Refactoring / Bug Fixes" section, or just
  delete it from `firmware-issue.md`.
- **`firmware-issue.md::FW-ISSUE-4`** ("`MAX_WHEEL_SPEED_MMS = 3500`
  too loose") now has a measured baseline: `test-report.md §9.2` shows
  worst-case combined wheel speed at firmware velocity caps is ~1.94 m/s.
  Recommendation: tighten `MAX_WHEEL_SPEED_MMS` to 2200 (10 % margin).

---

## See also

- `firmware-issue.md` — earlier open issues
- `firmware-changelog.md` — fixed items (verify before re-investigating)
- `test-report.md` — live verification snapshots, §9 is this audit's tests
