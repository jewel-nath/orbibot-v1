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

Rewritten 2026-08-03, when the compute was replaced.

---

## The prompt

```text
আমরা OrbiBot-এ Phase 0 চালিয়ে যাচ্ছি — নতুন কম্পিউটার সেটাপ।

শুরু করার আগে পড়ে নাও:
  docs/operations/computer-setup.md — এই মুহূর্তের কাজ, ধাপে ধাপে
  docs/plan/roadmap.md              — নয়টা phase আর প্রতিটার gate
  .claude/rules/robot-safety.md     — রোবট আর পাওয়ার ছোঁয়ার নিয়ম
  docs/moc/backlog-moc.md           — খোলা finding কোথায় কোথায় আছে

অবস্থা: Raspberry Pi 5 বাদ দেওয়া হয়েছে — যেকোনো real workload-এ
চারটা কোরই 100% হয়ে যেত। এখন Beelink SER5 Pro (Ryzen 7 PRO 5800H,
8C/16T, x86_64, 11.6 GiB, 457G NVMe)।

Beelink এখনো রোবটে লাগানো হয়নি — টেবিলে, নিজের charger-এ চলছে।
কোনো হার্ডওয়্যার লাগানো নেই: motor board নেই, LiDAR নেই, camera নেই।
মানে এখন কোনো কমান্ডে চাকা ঘুরবে না — কিন্তু অপারেটর যেকোনো সময়
তার লাগিয়ে দিতে পারে, আর তোমাকে বলা হবে না। ধরে নেবে না;
/dev/motordriver আছে কিনা দেখে নেবে।

তোমার sudo নেই — .claude/settings.json এ deny করা আছে, ইচ্ছে করেই।
ইনস্টলের কাজ অপারেটর করবে: ./scripts/setup_computer.sh
তুমি স্ক্রিপ্ট লিখবে/ঠিক করবে, আর ./scripts/setup_computer.sh verify
দিয়ে কী হয়েছে কী বাকি দেখবে।

আমি রোবটের পাশে আছি। যা করতে বলবে করব — কিন্তু আমাকে
স্পষ্ট করে বলতে হবে, একবারে একটা কাজ, তারপর অপেক্ষা করবে।

পাঁচটা জিনিস মনে রাখবে:
  - Power: এক ব্যাটারি থেকেই সব। 12.8V → RBD-2767 boost → 19V → Beelink,
    আর সেই একই পয়েন্ট থেকে ROSMaster board। 10A fuse ইনপুট দিকে।
    Beelink লাগানোর আগে multimeter দিয়ে converter output মাপতেই হবে।
  - CPU দিয়ে justify করা প্রতিটা tuning value এখন অচল — nav2_params,
    slam_params, dashboard budget। ওগুলো TODO দিয়ে মার্ক করা আছে।
    scale করবে না, নতুন করে মেপে বের করবে।
  - Magnetometer নেই, ইচ্ছে করেই বাদ। ফেরত আনার প্রস্তাব দেবে না।
  - Teleop শুধু web dashboard থেকে — joy ইনস্টল করবে না।
  - `raspberry_pi` branch হল Pi-যুগের ব্যাকআপ। ছোঁবে না, merge করবে না,
    আর কখনো force-push করবে না।

কাজ শুরুর আগে বলো: Phase 0-এর কোন ধাপটা এখন বাকি আর কেন,
আর তার জন্য আমাকে কী করতে হবে।
```

---

## Where things stand — 2026-08-03

- **The computer changed today.** Pi 5 → Beelink SER5 Pro. Roughly 4–6× the
  CPU, and x86_64 instead of aarch64. The Pi's state is on the `raspberry_pi`
  branch; do not delete or merge it.
- **The Beelink is on a bench, on its own charger.** Nothing is wired to it and
  ROS 2 is not installed. `./scripts/setup_computer.sh verify` reports what is
  present.
- **The operator is mid-way through the electronics.** Boost converter and 10 A
  fuse are bought; wiring is not finished.
- **The firmware is unaffected.** Everything verified in `test-report.md` is
  STM32-side and survived the host swap — that is the two-computer split in
  [[system-overview]] working as designed.

### Decisions taken today

| Decision | Consequence |
|---|---|
| One battery for robot and computer | 12.8 V node feeds ROSMaster *and* the boost converter. Motor transients land on the computer's rail |
| Pi 5 removed entirely, not kept | No multi-machine DDS setup to maintain |
| RealSense depth **enabled** | The driver is back in the graph; the v4l2 bypass in [[dashboard-design]] is superseded |
| Simulation optional, not now | Possible on this hardware, but off the critical path |

### Open, and blocking

| # | What | Why it blocks |
|---|---|---|
| 1 | **Beelink adapter label unread** | The whole 19 V power design assumes 65 W. Some Beelink models are 12 V, which would make the boost converter the wrong part |
| 2 | P-1…P-5 power measurements | The converter's 10 V minimum sits 0.5 V below the BMS cutoff. A brown-out during an NVMe write corrupts the filesystem |
| 3 | Robot not re-weighed | Phase 1 calibration against the old mass is wasted work |
| 4 | No CPU baseline | Phases 3, 5 and 6 have nothing to budget against |

## What the agent already knows

It does not need telling — these load automatically or it will read them:

| Source | Gives it |
|---|---|
| `CLAUDE.md` | Architecture, build commands, conventions, the docs map |
| `.claude/rules/robot-safety.md` | Power/wiring order, BOOT0 sequence, elevated vs ground |
| `.claude/rules/docs-sync.md` | Which document a change makes untrue |
| `docs/operations/computer-setup.md` | The current runbook, stage by stage |
| `docs/plan/roadmap.md` | Nine phases and every gate |
| `test-report.md` | What has been verified live, and when |

## Phase 0 gate

- [ ] Adapter label read; converter output set and verified before load
- [ ] Rail **> 11.5 V** and converter output **> 18 V** through a four-motor burst
- [ ] Ten motor start/stop cycles, computer logged in: no reboot, no `dmesg` reset
- [ ] `colcon build` clean, **12 packages**
- [ ] `/dev/motordriver` and `/dev/lidar` on boot
- [ ] RealSense at **5000 Mbps**, depth + colour together
- [ ] New mass and footprint in [[inventory]]
- [ ] CPU baseline recorded

## Related

[[roadmap]] · [[computer-setup]] · [[backlog-moc]] · [[docs/README|Docs home]]
