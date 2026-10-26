# OrbiBot Hardware Study Guide

**Hardware Interface Package - From Driver to ROS2 Node**

Welcome! This guide teaches you the `orbibot_hardware` package - the bridge between OrbiBot's physical hardware and ROS2.

---

## Prerequisites

**REQUIRED:** Complete before starting:

1. **[ROS2 Study Guide](../ros2/)** - Common ROS2 fundamentals
   - Minimum: 00-ros2-overview, 03-topics-pub-sub, 05-services, 07-parameters
   - Essential: Nodes, Topics, Services, Parameters

2. **Basic Python** - Variables, functions, classes
3. **Linux basics** - Terminal navigation

---

## What You'll Learn

By completing this guide, you will understand:

- **Hardware Interface Design** - How software talks to physical robots
- **Serial Communication** - Binary protocols and packet structures
- **Sensor Integration** - IMU, encoders, and data fusion
- **Safety Systems** - Timeouts, battery monitoring, emergency stops
- **Real-World Debugging** - Tools and techniques for troubleshooting

---

## Study Files

### Foundation
| File | Topic | Time |
|------|-------|------|
| [00 - What is a Hardware Interface?](00-what-is-hardware-interface.md) | What is hardware interface? | 10 min |
| [02 - Hardware Architecture](02-hardware-architecture.md) | System architecture | 15 min |

### Core Concepts
| File | Topic | Time |
|------|-------|------|
| [03 - Serial Communication](03-serial-communication.md) | Serial protocols | 25 min |
| [04 - Hardware Node Deep Dive](04-hardware-node-deep-dive.md) | hardware_node.py analysis | 45 min |
| [05 - Driver Deep Dive](05-driver-deep-dive.md) | rosmaster_driver.py analysis | 40 min |

### Practice
| File | Topic | Time |
|------|-------|------|
| [10 - Debugging Guide](10-debugging-guide.md) | Troubleshooting | 30 min |
| [11 - Practical Exercises](11-practical-exercises.md) | Hands-on exercises | 60 min |

---

## Learning Path

### Week 1: Prerequisites + Foundation
- Complete [ROS2 guide](../ros2/) topics 00, 03, 05, 07
- Read 00-what-is-hardware-interface.md
- Read 02-hardware-architecture.md

### Week 2: Core Code
- 03-serial-communication.md
- 04-hardware-node-deep-dive.md
- 05-driver-deep-dive.md

### Week 3: Practice
- 10-debugging-guide.md
- 11-practical-exercises.md

---

## Related Files

```
src/orbibot_hardware/
├── orbibot_hardware/
│   ├── hardware_node.py       ← Main ROS2 node
│   ├── rosmaster_driver.py    ← Serial driver
│   └── system_monitor.py      ← System monitoring
├── config/
│   └── hardware_params.yaml   ← Configuration
├── launch/
│   └── hardware.launch.py     ← Launch file
└── known-issues.md          ← Known issues
```

---

## Start Here

**Begin with:** [00 - What is a Hardware Interface?](00-what-is-hardware-interface.md)

---

**Happy Learning!**