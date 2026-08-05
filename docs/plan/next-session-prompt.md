---
title: "Next Session Prompt"
type: plan
tags:
  - plan
  - session
---

# Next Session Prompt

Paste the block below into a fresh Claude Code session on the robot's computer.
Everything else it needs — the phases, the protocol, the measured history — it
will read for itself.

Rewritten **2026-08-04**. The previous version was written on 2026-08-03 before
the software bring-up and described a bench machine with no ROS 2 and no
hardware attached. All of that is now false, which is exactly the failure mode
`.claude/rules/docs-sync.md` exists to prevent: a confidently wrong document
that the next agent trusts. **Rewrite this file whenever the machine's state
changes, not when someone notices.**

---

## The prompt

```text
আমরা OrbiBot-এ কাজ করছি — Phase 0 শেষ পর্যায়ে, Phase 2 চলছে।

শুরু করার আগে পড়ে নাও:
  docs/plan/roadmap.md              — নয়টা phase আর প্রতিটার gate
  .claude/rules/robot-safety.md     — রোবট আর পাওয়ার ছোঁয়ার নিয়ম
  docs/moc/backlog-moc.md           — খোলা finding কোথায় কোথায় আছে
  docs/operations/computer-setup.md — মেশিন সেটাপ + পাওয়ার runbook

কম্পিউটার: Beelink SER5 Pro (Ryzen 7 PRO 5800H, 8C/16T, x86_64,
11.6 GiB, 457G NVMe)। Raspberry Pi 5 বাদ — যেকোনো real workload-এ
চারটা কোরই 100% হয়ে যেত। Pi-যুগ `raspberry_pi` branch-এ রাখা আছে;
ছোঁবে না, merge করবে না, force-push করবে না।

সফটওয়্যার তৈরি: ROS 2 Jazzy আছে, ১২টা প্যাকেজ build হয়, udev rule
কাজ করে (/dev/motordriver, /dev/lidar), PlatformIO আছে
(~/.platformio-venv/bin/pio — পুরনো ~/.platformio/penv পথটা আর নেই)।

হার্ডওয়্যার লাগানো আছে: ROSMaster board, RPLidar A1, RealSense D435।
মানে **কমান্ডে চাকা ঘুরতে পারে**। কিন্তু Beelink এখনো রোবটে মাউন্ট করা
হয়নি — সেটা Phase 0-এর বাকি কাজ। কোনো অবস্থা ধরে নেবে না, দেখে নেবে।

তোমার sudo নেই — passwordless grant তুলে নেওয়া হয়েছে, ইচ্ছে করেই।
sudo দিলে password prompt-এ আটকে যাবে। ইনস্টলের কাজ অপারেটরের:
./scripts/setup_computer.sh <stage>। তুমি স্ক্রিপ্ট লিখবে/ঠিক করবে,
আর ./scripts/setup_computer.sh verify দিয়ে কী আছে কী নেই দেখবে।

আমি রোবটের পাশে আছি। যা করতে বলবে করব — কিন্তু আমাকে
স্পষ্ট করে বলতে হবে, একবারে একটা কাজ, তারপর অপেক্ষা করবে।

পাঁচটা জিনিস মনে রাখবে:
  - Power: এক ব্যাটারি থেকেই সব। 12.8V → RBD-2767 boost → 19V → Beelink,
    আর সেই একই পয়েন্ট থেকে ROSMaster board। 10A fuse ইনপুট দিকে।
    P-3 মাপা হয়ে গেছে (§9.11) — রোবট নিজের ব্যাটারিতে চলে, ০.৪৫ m/s পর্যন্ত
    সবচেয়ে বেশি সাগ ০.২০ V, মার্জিন ০.৭১ V, কম্পিউটার রিসেট হয়নি। তবে
    প্যাকটা ভরা ছিল — কাটঅফের কাছে সাগ এখনো মাপা হয়নি। P-1/P-2/P-4 বাকি,
    ওগুলোয় কনভার্টারে মাল্টিমিটার লাগবে।
  - CPU দিয়ে justify করা প্রতিটা tuning value অচল — nav2_params,
    slam_params, dashboard budget। scale করবে না, নতুন করে মেপে বের করবে।
  - Magnetometer নেই, ইচ্ছে করেই বাদ। ফেরত আনার প্রস্তাব দেবে না।
  - Teleop শুধু web dashboard থেকে — joy ইনস্টল করবে না।
  - কার্নেল লগ পড়তে `journalctl -k`, `dmesg` নয় — dmesg_restrict চালু,
    dmesg কিছুই পড়তে পারে না অথচ grep -c আত্মবিশ্বাসের সাথে 0 দেয়।

কাজ শুরুর আগে বলো: এখন কোন ধাপটা বাকি আর কেন, আর আমাকে কী করতে হবে।
```

---

## Where things stand — 2026-08-04

### Done, and verified on this machine

| | Evidence |
|---|---|
| ROS 2 Jazzy, toolchain, `twist_mux`, RealSense driver installed | `setup_computer.sh verify` |
| **12 packages** build clean on x86_64 — 17.9 s (Pi took ~40 s) | `colcon build` |
| udev: `/dev/motordriver` → `ttyUSB0`, `/dev/lidar` → `ttyUSB1` | present across reboots |
| Firmware builds: 24.7 KB flash (9.7 %), 21.6 KB RAM (45.1 %), 89 s | `pio run` |
| Frontend builds: 816 K `dist/` | `npm run build` |
| Full stack launches; `/odom`, `/imu/*`, `/scan`, TF all publishing | 2026-08-03 live run |
| CPU + thermal baseline, idle and stack-up | [[baseline-results]] |
| P-5 — no brown-out or reset through a motor run | `test-report.md` §9.6 |

### Not done — Phase 0's remaining gate

| # | What | Who |
|---|---|---|
| 0.6 | RealSense at **5000 Mbps** — stuck at 480, original cable being fitted | operator |
| 0.8 | **Mount the Beelink, converter and fuse on the robot** | operator |
| 0.9 | Re-weigh, re-measure the footprint | operator |
| 0.10 | P-1, P-2, P-4 (multimeter, converter temperature); **P-3 on the ground** | operator, then together |
| 0.11 | CPU baseline *while driving* — the idle half is recorded | together |

**0.8 is the critical path.** Nothing in Phase 1 can be measured before it,
because mounting changes mass and centre of gravity, and every Phase 1 number
depends on both.

### Open findings

| ID | What | Where |
|---|---|---|
| SENS-2 | RealSense enumerates at 480 Mbps, blocking the depth decision | `sensors-issue.md` |
| CC-2 | Accel X/Y scale unconfirmed under real acceleration | [[backlog-moc]] |
| FW-ISSUE-4 | M4 runs 12–15 % slow at full speed | `firmware-issue.md` |

Closed 2026-08-04:

| ID | Outcome |
|---|---|
| **HW-BUG-8** | **Fixed.** Not the firmware and not board uptime — `MultiThreadedExecutor` cost the node a third of its rate under `/cmd_vel` load. Now 50.00 Hz driven or parked, at 9.75 % CPU |
| **BRINGUP-2** | Fixed — the LiDAR was opening `/dev/motordriver` via a shared launch-argument name |
| **BRINGUP-3** | Not a bug — `/odom` at 1.94 Hz is the designed on-change + heartbeat behaviour |
| **SENS-1** | Resolved — `/scan` at 8.0 Hz is the A1's device rate; the documented 10 Hz was the datasheet maximum |
| **CC-1** | Done — `twist_mux` is the single writer of `/cmd_vel`, 8/8 acceptance, stop in 286 ms |
| **FW-ISSUE-12** | `SET_MOTOR = 0x09` was fiction; the test that used it is withdrawn and a table-agreement guard added |

BRINGUP-1 was re-characterised rather than closed: real Ctrl+C stops everything
in 1.1 s, and the variable is the controlling terminal, not the launch file.

Fixed 2026-08-03: **HW-BUG-9** — the launch armed all four motors six seconds
after start. `motors_enabled` now defaults to `false`.

### Decisions that hold

| Decision | Consequence |
|---|---|
| One battery for robot and computer | Motor transients land on the computer's rail. P-1…P-5 exist for this; **P-3 measured 2026-08-05 — 0.20 V sag, 0.71 V margin, healthy pack only** (§9.11) |
| Pi 5 removed entirely, not kept | No multi-machine DDS setup to maintain |
| RealSense depth **enabled** | The driver owns the device; the v4l2 bypass in [[dashboard-design]] is superseded |
| Simulation possible, not now | Off the critical path — see *Optional* in [[roadmap]] |
| Phase 2 pulled ahead of Phase 1 | Phase 1 is the first driving on the floor. It should not happen on an unarbitrated `/cmd_vel` with no e-stop |

## What the agent already knows

It does not need telling — these load automatically or it will read them:

| Source | Gives it |
|---|---|
| `CLAUDE.md` | Architecture, build commands, conventions, the docs map |
| `.claude/rules/robot-safety.md` | Power/wiring order, BOOT0 sequence, elevated vs ground |
| `.claude/rules/docs-sync.md` | Which document a change makes untrue |
| `docs/plan/roadmap.md` | Nine phases and every gate |
| `test-report.md` | What has been verified live, and when |
| `src/<pkg>/<pkg>-issue.md` | What is open, per package |

## Traps this project has already fallen into

Written down because each one cost real time, and each one looked like a pass:

- **`dmesg` reads nothing here.** `kernel.dmesg_restrict` is set, so
  `dmesg | grep -c` returns a confident `0` having read no log. Use
  `journalctl -k`.
- **Reading the node is not reading the launch.** `hardware_node.py` never
  enables motors; `hardware.launch.py` did, on a timer. The answer you get
  depends on which file you opened — open both.
- **A power test with the charger plugged in measures the charger.** P-3 was run
  that way once and had to be thrown away.
- **A compensation factor can hide a misconfigured register for four months.**
  Fix the cause, not the reading — see Principle 3 in [[roadmap]].

## Related

[[roadmap]] · [[computer-setup]] · [[backlog-moc]] · [[command-pipeline]] ·
[[baseline-results]] · [[docs/README|Docs home]]
