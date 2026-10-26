# Learning path

70 lessons that take you from "what is an embedded system" to a working
understanding of OrbiBot's stack. Each lesson is one topic, 10–35 minutes,
written to be readable without prior robotics experience.

These teach **concepts through this robot's actual code**. For API reference,
read the package `README.md`; for design decisions, see [System Overview](../architecture/system-overview.md).

---

## Prerequisites

Basic Linux command line, Python or C++ fundamentals, Git, and high-school
maths (algebra and trigonometry). Nothing else is assumed.

## Stage 1 — Foundation

| Area | Lessons | Covers |
|---|---|---|
| [ROS 2](ros2/README.md) | 13 | Nodes, executors, topics, services, actions, parameters, launch, TF2, bags, RViz, CLI |

Every package uses ROS 2, so this is learned once rather than repeated per
package.

## Stage 2 — Hardware and firmware

| Area | Lessons | Package | Covers |
|---|---|---|---|
| [Firmware](firmware/README.md) | 28 | [orbibot_rosmaster_firmware](../../src/orbibot_rosmaster_firmware/README.md) | Embedded basics, STM32, FreeRTOS, serial protocol, mecanum maths, PID, odometry |
| [Hardware](hardware/README.md) | 8 | [orbibot_hardware](../../src/orbibot_hardware/README.md) | The ROS 2 driver, serial comms, node and driver walkthroughs, debugging |

Either is a valid entry point after ROS 2 — start with firmware for embedded
systems, hardware for ROS 2 software.

## Stage 3 — Robot systems

| Area | Lessons | Package | Needs first |
|---|---|---|---|
| [Description](description/README.md) | 6 | [orbibot_description](../../src/orbibot_description/README.md) | ROS 2 |
| [Sensors](sensors/README.md) | 7 | [orbibot_sensors](../../src/orbibot_sensors/README.md) | ROS 2, hardware |
| [Localization](localization/README.md) | 8 | [orbibot_localization](../../src/orbibot_localization/README.md) | ROS 2, hardware, sensors |

---

## Suggested routes

**Complete stack** — ROS 2 → firmware → hardware → description → sensors →
localization. Roughly 8–10 weeks part-time.

**Software only, skip the STM32** — ROS 2 → hardware → description → sensors →
localization.

**Embedded only** — ROS 2 basics → firmware, all 28 lessons.

**"I just want to run it"** — skip the lessons; go to [Getting started](../getting-started.md) and
[Running the robot](../operations/running.md).

---

## Not yet written

Areas that exist as packages but have no lesson set: SLAM, navigation,
exploration, webgui and agent. For those, read the package READMEs listed in
[Packages](../packages.md), and the source.

## Related

[Docs home](../README.md) · [Packages](../packages.md) · [System Overview](../architecture/system-overview.md)
