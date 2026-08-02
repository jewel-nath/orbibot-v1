---
title: "Learning Path"
type: moc
tags:
  - moc
  - learn
---

# Learning Path

71 lessons that take you from "what is an embedded system" to a working
understanding of OrbiBot's stack. Each lesson is one topic, 10–35 minutes,
written to be readable without prior robotics experience.

These teach **concepts through this robot's actual code**. For API reference,
read the package `README.md`; for design decisions, see [[system-overview]].

---

## Prerequisites

Basic Linux command line, Python or C++ fundamentals, Git, and high-school
maths (algebra and trigonometry). Nothing else is assumed.

## Stage 1 — Foundation

| Area | Lessons | Covers |
|---|---|---|
| [[ros2-moc\|ROS 2]] | 13 | Nodes, executors, topics, services, actions, parameters, launch, TF2, bags, RViz, CLI |

Every package uses ROS 2, so this is learned once rather than repeated per
package.

## Stage 2 — Hardware and firmware

| Area | Lessons | Package | Covers |
|---|---|---|---|
| [[firmware-moc\|Firmware]] | 28 | [[orbibot_rosmaster_firmware]] | Embedded basics, STM32, FreeRTOS, serial protocol, mecanum maths, PID, odometry |
| [[hardware-moc\|Hardware]] | 8 | [[orbibot_hardware]] | The ROS 2 driver, serial comms, node and driver walkthroughs, debugging |

Either is a valid entry point after ROS 2 — start with firmware for embedded
systems, hardware for ROS 2 software.

## Stage 3 — Robot systems

| Area | Lessons | Package | Needs first |
|---|---|---|---|
| [[description-moc\|Description]] | 7 | [[orbibot_description]] | ROS 2 |
| [[sensors-moc\|Sensors]] | 7 | [[orbibot_sensors]] | ROS 2, hardware |
| [[localization-moc\|Localization]] | 8 | [[orbibot_localization]] | ROS 2, hardware, sensors |

---

## Suggested routes

**Complete stack** — ROS 2 → firmware → hardware → description → sensors →
localization. Roughly 8–10 weeks part-time.

**Software only, skip the STM32** — ROS 2 → hardware → description → sensors →
localization.

**Embedded only** — ROS 2 basics → firmware, all 28 lessons.

**"I just want to run it"** — skip the lessons; go to [[testing-guide]] and
[[orbibot_bringup]].

---

## Not yet written

Areas that exist as packages but have no lesson set: SLAM, navigation,
exploration, webgui and agent. For those, read the package hub notes in
[[packages-moc]] and the source.

Eight individual lessons are linked from existing notes but were never written —
they show as unresolved links in graph view. The list is in [[backlog-moc]].

## Related

[[docs/README|Docs home]] · [[packages-moc]] · [[system-overview]]
