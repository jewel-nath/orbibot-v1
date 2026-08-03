---
title: "OrbiBot Docs"
type: moc
tags:
  - moc
  - home
---

# OrbiBot

Mecanum-wheeled indoor robot. ROS 2 Jazzy on a **Beelink SER5 Pro**, motor
control on a Yahboom ROSMaster V3.0 (STM32F103RCT6) over serial at 115200 baud.

> ⚠️ **Migration in progress — 2026-08-03.** The Raspberry Pi 5 hit 100 % CPU
> under any real workload and has been replaced. **The Beelink is on a bench,
> not on the robot** — nothing is wired to it and ROS 2 is not installed.
> Start at [[computer-setup]]. The Pi's state lives on the `raspberry_pi`
> branch.

Once the hardware is connected, commands here move real wheels —
`.claude/rules/robot-safety.md` first.

---

## Start here

| You want | Go to |
|---|---|
| **To set up the new computer** | [[computer-setup]] — power, ROS 2, build, mounting |
| What to build next | [[roadmap]] — phases, and the numbers that gate each one |
| What is broken | [[backlog-moc]] — where every open finding lives |
| How the pieces connect | [[system-overview]] |
| Who is allowed to drive the robot | [[command-pipeline]] |
| Dashboard architecture | [[dashboard-design]] — CPU budget void, being re-derived |
| One package | [[packages-moc]], then that package's own `README.md` |
| Learning a subsystem from zero | [[learn-moc]] — 71 lessons, six areas |
| The board itself — pinout, timers, rails | [[rosmaster-board]] |
| What hardware is actually fitted | [[inventory]] |
| How another robot solved this | [[yahboom-rosmaster-x3]], [[lgdxrobot2]], [[aubot]] |

---

## Where truth lives

**The code decides.** If a note disagrees with the code, the note is a bug.

Documentation sits **beside the code it describes**, not in here:

```
src/<pkg>/README.md            the API — topics, services, parameters
src/<pkg>/<pkg>-issue.md       what is open, with severity
src/<pkg>/<pkg>-changelog.md   what changed and why
testing-guide.md               procedures and pass criteria
src/orbibot_rosmaster_firmware/test-report.md
                               what has been verified live, and when
```

`docs/` holds what has nowhere else to go: **why** the system is shaped this
way, **what is planned**, **what was measured**, and **how to learn it**. Notes
here point at the per-package files rather than copying them — a copy is a
future contradiction.

## Reading this as a vault

The Obsidian vault root is the **repository root**, not `docs/`. That is
deliberate: it lets a note link straight to `[[firmware-architecture]]` or
`[[testing-guide]]` where they actually live, in `src/` and at the top level.

`docs/COLCON_IGNORE` keeps colcon out of this tree.

## Related

[[roadmap]] · [[computer-setup]] · [[backlog-moc]] · [[packages-moc]] ·
[[learn-moc]] · [[system-overview]]
