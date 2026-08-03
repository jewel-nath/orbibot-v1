---
title: "Next Session Prompt"
type: plan
tags:
  - plan
  - session
---

# Next Session Prompt

Paste the block below into a fresh Claude Code session (Fable 5) on the robot's
Pi. Everything else it needs — the phases, the protocol, the measured history —
it will read for itself.

---

## The prompt

```text
আমরা OrbiBot-এ Phase 1 শুরু করব।

শুরু করার আগে পড়ে নাও:
  docs/plan/roadmap.md            — ধাপগুলো আর প্রতিটার gate
  .claude/rules/robot-safety.md   — রোবট ছোঁয়ার নিয়ম
  docs/moc/backlog-moc.md         — খোলা finding কোথায় কোথায় আছে
  src/orbibot_rosmaster_firmware/test-report.md — এ পর্যন্ত যা মাপা হয়েছে

Phase 1-এর কাজগুলো একটা একটা করে ধরবে, লাফ দেবে না।
প্রতিটার পরে: হার্ডওয়্যারে টেস্ট → সংখ্যা লিখে রাখো → commit করো।
Phase 1-এর gate না মিটলে Phase 2-এ যাবে না।

আমি রোবটের পাশে আছি। যা করতে বলবে করব — কিন্তু আমাকে
স্পষ্ট করে বলতে হবে, একবারে একটা কাজ, তারপর অপেক্ষা করবে:

  - firmware flash করার আগে: BOOT0 jumper কোন দিকে, RESET কখন চাপব
  - মোটর চালানোর আগে: রোবট উপরে (চাকা ফাঁকা) নাকি নিচে দরকার
  - জায়গা লাগলে: কতটুকু ফাঁকা লাগবে

রোবট এখন একটা টুলের উপরে, চাকা ফাঁকা। নিচে নামাতে হলে বলো।

তিনটে জিনিস মনে রাখবে:
  - Magnetometer নেই, ইচ্ছে করেই বাদ দেওয়া। ফেরত আনার প্রস্তাব দেবে না।
  - Teleop শুধু web dashboard থেকে — Pi-তে gamepad/joy লাগবে না।
  - `restructure-aug03` branch আর `pre-reconcile-aug03` tag ব্যাক-আপ,
    পুরোনো একটা ইতিহাসের। ওগুলো ছোঁবে না, merge করবে না,
    আর কখনো force-push করবে না। `main` GitHub-এর সাথে মিলে আছে।

আরেকটা কাজ আছে: docs/ আর src/<pkg>/README.md আমি আগের সেশনে
কোড পড়ে লিখেছি, কিন্তু ক্রস-চেক করা হয়নি। কোনো package-এ কাজ
করার আগে ওর ডক আর কোড মিলিয়ে দেখো — না মিললে কোড জেতে,
ডকটা বাগ, ঠিক করে দাও।

কাজ শুরুর আগে বলো: Phase 1-এর কোন কাজটা প্রথমে ধরছ আর কেন,
আর তার জন্য রোবট কোন অবস্থায় লাগবে।
```

---

## What the agent already knows

It does not need telling — these load automatically or it will read them:

| Source | Gives it |
|---|---|
| `CLAUDE.md` | Architecture, build commands, conventions, the docs map |
| `.claude/rules/robot-safety.md` | BOOT0 sequence, elevated vs ground, stopping, reporting |
| `.claude/rules/docs-sync.md` | Which document a change makes untrue |
| `docs/plan/roadmap.md` | Seven phases and every gate |
| `test-report.md` | What has been verified live, and when |
| `firmware-issue.md` | What is still open on the board |

## Where things stand — 2026-08-03

Read this before wondering why the repo looks the way it does.

- **The board runs firmware built from this branch.** Flashed and verified
  today: `|a| = 9.802 m/s²`, ratio to g **0.9995**; raw IMU 50 Hz in 12-byte
  packets. `test-report.md` §9.4 and §9.5.
- **The workspace builds clean** — 12 packages, ~40 s. The 13th is the firmware,
  which carries `COLCON_IGNORE`.
- **`main` is in sync with GitHub.** Today reconciled two histories that had
  diverged: this Pi's clone had gone stale in March while ~90 commits of work
  were pushed from elsewhere. GitHub's line won; the verified work from the
  stale line was replayed on top.
- **`restructure-aug03` and the tag `pre-reconcile-aug03` are backups** of the
  stale line. Leave them alone. Do not merge them, and do not force-push.

## Phase 1 at a glance

1.8 and 1.9 need no robot. 1.7 starts **elevated** and finishes on the ground.
Everything else needs the robot **on the ground**.

| # | Task | Robot state |
|---|---|---|
| 1.1 | Wheel radius / encoder CPR — drive a measured 2 m | ground, ~3 m clear |
| 1.2 | Rotation — 10 × 360° in place | ground, ~1.5 m clear |
| 1.3 | Yaw drift rate, stationary, 10 min | ground, still |
| 1.4 | Forward/backward velocity asymmetry | ground |
| 1.5 | Accel X/Y scale under known acceleration | ground |
| 1.6 | Re-tune motor PID under load, save to flash | ground |
| 1.7 | Real max wheel speed per motor; M4's 12–15 % deficit | elevated, then ground |
| 1.8 | Host-side unit tests | none |
| 1.9 | One source of truth for the protocol table | none |

**Start with 1.8 and 1.9** — no hardware, and 1.9 removes the class of bug that
once cost a whole sensor. Then 1.1–1.5 together in one clear-floor session.

## Gate before Phase 2

- Straight 2 m: odometry error **< 3 %**, forward and backward
- 10 × 360°: accumulated yaw error **< 5°** total
- Yaw drift, stationary, 10 min: recorded
- Forward and backward at equal commanded speed agree within **5 %**
- `|a|` within **1 %** of g through a slow tilt, all three axes
- Unit tests green with no hardware attached

## Related

[[roadmap]] · [[backlog-moc]] · [[docs/README|Docs home]]
