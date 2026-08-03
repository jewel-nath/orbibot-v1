# Hardware-in-the-Loop Rules

**This robot is real. It has motors, a battery, and a human near it.**

Claude Code runs on the robot's own computer — a **Beelink SER5 Pro** since
2026-08-03, replacing a Raspberry Pi 5.

> **Right now that machine is on a bench and nothing is wired to it** — no
> ROSMaster board, no LiDAR, no camera. Commands do not currently reach a
> motor. **Do not treat that as permanent.** The moment the operator plugs the
> hardware in, every rule below applies, and you will not necessarily be told.
> Check for `/dev/motordriver` before assuming either way.

The operator is present and will do any physical action you ask for — but
**only if you ask clearly and then wait**.

---

## The one rule

**Never assume a physical action happened. State it, wait for confirmation,
then continue.**

A physical action is anything a human must touch: a jumper, a button, a cable,
picking the robot up, putting it down, clearing a space.

Ask for **one action at a time**. Say exactly what to touch and what to expect.
Then stop and wait.

---

## Power and wiring

New hazard class as of 2026-08-03. The Pi took 5 V from the ROSMaster board's
Type-C. The Beelink takes ~19 V through a **RBD-2767 boost converter** off the
same 12.8 V node that feeds the motor board:

```
4S LiFePO4 ──┬── ROSMaster V3.0 ── motors
   12.8V     │
             └── 10A fuse ── RBD-2767 boost ── 19V ── Beelink
```

**One battery, one node, shared with four motors.** That is the operator's
chosen topology, and it has a consequence worth stating plainly rather than
discovering: motor current transients sag the same rail the computer runs on.

Three rules follow.

1. **Never ask for the Beelink to be connected before the converter output has
   been measured.** The multi-turn pot ships at an arbitrary position and its
   range reaches 35 V. Order is always: battery → converter input → *measure
   with a multimeter* → adjust to the target → **then** the computer.
2. **The target voltage comes from the adapter label, not from you.** If it has
   not been read, say so and wait. Do not carry the 19 V assumption in this
   repo into a wiring instruction.
3. **A brown-out is not a reboot.** The converter's 10 V minimum input sits
   0.5 V below the BMS cutoff at 10.5 V. If the rail dips while the NVMe is
   writing, the filesystem corrupts. Until P-1…P-5 in
   `docs/operations/computer-setup.md` are measured and recorded, treat *"can the
   robot drive on battery with the computer up"* as **unanswered** — do not
   assume it either way.

Before any command that spins motors while the Beelink runs on battery: ask
whether P-1…P-5 have been done. If not, say what could go wrong and let the
operator decide.

## Flashing firmware

The board has no auto-bootloader circuit, so BOOT0 and RESET are always manual.
This sequence is mandatory:

1. **Build first.** Never ask for a jumper before `pio run` succeeds — do not
   spend the operator's hands on a build that fails.
   ```bash
   cd src/orbibot_rosmaster_firmware && ~/.platformio/penv/bin/pio run
   ```
2. **Ask, then wait:**
   > **BOOT0 jumper HIGH (3.3V) করুন, তারপর RESET চাপুন** — হয়ে গেলে বলুন।
3. Upload only after they confirm:
   ```bash
   ~/.platformio/penv/bin/pio run --target upload
   ```
4. **Ask, then wait:**
   > **BOOT0 jumper LOW (GND) করুন, তারপর RESET চাপুন** — হয়ে গেলে বলুন।
5. **Verify the flash took.** Query the version, or better, measure the thing
   you changed. "Upload succeeded" is not evidence the firmware is correct.

If you need boot messages, `ENABLE_BOOT_MESSAGES` in `orbibot_config.h` is `0`
in production. Turning it to `1` costs an extra flash cycle in each direction —
plan both before asking for the first one.

## Moving the robot

Two states, and they are not interchangeable:

| State | Safe for | Not valid for |
|---|---|---|
| **Elevated** (on a stool/blocks, wheels free) | Encoder direction, motor direction, PID step response, protocol tests | Anything measuring distance, drift, or traction |
| **On the ground**, ≥2 m clear | Odometry calibration, drift, PID under load, mapping, navigation | — |

Before commanding **any** motion:

1. State which state the test needs and why
2. Ask the operator to confirm the robot is in that state
3. Wait

Do not carry a state assumption across turns. If the robot was elevated an hour
ago, ask again.

When you need a change, ask plainly:
> **রোবট নিচে নামান, চারপাশে ~২ মিটার ফাঁকা রাখুন** — হয়ে গেলে বলুন।

## Before any motion at all

- Say **how to stop it**: kill the terminal, or cut power at the battery
- Keep test velocities low — 0.15 m/s is enough to measure almost anything
- Keep drive bursts short, seconds not minutes
- **Disable motors when the test ends** (`SetMotorEnable false`), every time
- Stop cleanly on the way out — leave no node publishing `cmd_vel`

## Reporting

- Report **numbers**, not adjectives. "|a| = 9.971, ratio 1.017", not "IMU looks fine".
- If a test fails, say so plainly with the output. Never round a failure up to a pass.
- If a result contradicts an earlier conclusion — including your own — say that
  directly and correct the record. This has already happened once on this robot
  and cost real time.
- Write measurements into `src/orbibot_rosmaster_firmware/test-report.md` (dated
  sections) or the package's `<pkg>-issue.md`. A number that stays in the
  terminal is a number that gets re-measured.

## Teleop path

Teleop is **web dashboard only** — a controller plugged into the operator's
laptop, read by the browser's Gamepad API, sent over rosbridge.

The consequence is that **the network is the control path**. A dropped wifi
link is a runaway robot unless timeouts are real. Per-input timeouts in
`twist_mux` and the driver's `cmd_timeout` are safety features here, not
housekeeping. The firmware enforces its own 2 s command timeout as the last
line — verified live, `test-report.md` §7.1.

`orbibot_teleop` (gamepad on the Pi via `/joy`) is **not in use**. Leave the
package in place as a network-independent fallback, but do not install
`ros-jazzy-joy` or wire it up unless the operator asks.

## Related

- `testing-guide.md` — procedures and pass criteria
- `src/orbibot_rosmaster_firmware/test-report.md` — what has been verified live, and when
- `src/orbibot_rosmaster_firmware/firmware-issue.md` — what is still open on the board
- `.claude/scripts/preflight.sh` — run before operating; `safety.sh` cross-checks
  the firmware and ROS 2 limits against each other
