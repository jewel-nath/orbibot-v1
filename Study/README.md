# OrbiBot Complete Study Guide

**From Zero to Master: Comprehensive Robotics Learning Path**

---

## 🎯 Learning Philosophy

This study documentation follows a **layered learning approach**:

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: Application Packages                              │
│  sensors | description | localization | slam | navigation   │
│  exploration | webgui | agent                               │
│                    ↓ Uses ROS2 concepts                     │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: Hardware Interface                                │
│  firmware (STM32) | hardware (ROS2 driver)                  │
│                    ↓ Uses embedded basics                   │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1: Common Foundation                                 │
│  ros2 (ROS2 fundamentals) - Shared across all packages      │
│                    ↓ Assumes basic programming              │
├─────────────────────────────────────────────────────────────┤
│  LAYER 0: Prerequisites                                     │
│  Basic Linux, Python/C++, Git, Math (high school level)     │
└─────────────────────────────────────────────────────────────┘
```

**Design Principles:**
- 📁 **Small focused files** - Each topic in its own file (10-35 min reading)
- 🔗 **Cross-referenced** - Links between related topics across packages
- 🏗️ **Progressive building** - Each layer builds on previous
- 🌍 **English only** - Accessible worldwide
- 🔄 **ROS2 reusable** - Common ROS2 concepts in one place

---

## 📚 Complete Study Path

### Prerequisites (External)
Before starting, you should know:
- Basic Linux command line
- Python or C++ fundamentals
- Git version control basics
- High school math (algebra, trigonometry)

### Stage 1: Common Foundation

| Folder | Package | Purpose | Duration |
|--------|---------|---------|----------|
| **[ros2/](ros2/)** | ROS2 Core | Common ROS2 concepts used by ALL packages | ~15 hours |

**Why separate ROS2 basics?** Every OrbiBot package uses ROS2. Learning it once saves repetition in each package guide.

### Stage 2: Hardware & Firmware

| Folder | Package | Purpose | Duration |
|--------|---------|---------|----------|
| **[firmware/](firmware/)** | orbibot_rosmaster_firmware | STM32 embedded programming | ~30 hours |
| **[hardware/](hardware/)** | orbibot_hardware | ROS2 hardware interface driver | ~15 hours |

**Learning Order:** 
1. Start with `firmware/` if you want to understand embedded systems
2. OR start with `hardware/` if you prefer software/ROS2 first
3. Both are independent entry points after `ros2/`

### Stage 3: Application Packages

| Folder | Package | Purpose | Duration | Prerequisites |
|--------|---------|---------|----------|---------------|
| **[description/](description/)** | orbibot_description | URDF, robot modeling | ~8 hours | ros2 |
| **[sensors/](sensors/)** | orbibot_sensors | Sensor drivers & fusion | ~12 hours | ros2, hardware |
| **[localization/](localization/)** | orbibot_localization | Position estimation | ~15 hours | ros2, hardware, sensors |
| **[slam/](slam/)** | orbibot_slam | Mapping | ~12 hours | ros2, localization |
| **[navigation/](navigation/)** | orbibot_navigation | Autonomous navigation | ~20 hours | ros2, localization, slam |
| **[exploration/](exploration/)** | orbibot_exploration | Autonomous exploration | ~10 hours | ros2, navigation |
| **[webgui/](webgui/)** | orbibot_webgui | Web dashboard | ~15 hours | ros2, hardware, sensors |
| **[agent/](agent/)** | orbibot_agent | AI agent integration | ~18 hours | ros2, navigation, exploration |

---

## 🗺️ Learning Paths

### Path A: Full Stack Developer (Complete)
**Goal:** Understand entire OrbiBot system

```
Month 1: Foundations
  Week 1-2: ros2/ (ROS2 fundamentals)
  Week 3-4: firmware/ (Embedded systems) OR hardware/ (Driver development)

Month 2: Core Systems
  Week 5: description/ (Robot modeling)
  Week 6: sensors/ (Sensor integration)
  Week 7-8: localization/ (Position tracking)

Month 3: Advanced Systems
  Week 9: slam/ (Mapping)
  Week 10-11: navigation/ (Autonomous movement)
  Week 12: exploration/ (Autonomous exploration)

Month 4: Application Layer
  Week 13: webgui/ (Web interface)
  Week 14-15: agent/ (AI integration)
  Week 16: Integration & Projects
```

**Total:** ~16 weeks (full-time pace) or ~8 months (part-time, 10hrs/week)

---

### Path B: Embedded Systems Engineer
**Goal:** Modify firmware and hardware drivers

```
Required:
  ros2/ → firmware/ → hardware/

Optional (for integration understanding):
  description/ → sensors/
```

---

### Path C: Navigation & AI Engineer
**Goal:** Work on autonomous navigation and AI

```
Required:
  ros2/ → hardware/ (basics) → sensors/ → localization/
  → slam/ → navigation/ → exploration/ → agent/

Skip:
  firmware/ (unless debugging hardware issues)
  webgui/ (unless building user interfaces)
```

---

### Path D: Web & Visualization Developer
**Goal:** Build dashboards and user interfaces

```
Required:
  ros2/ → hardware/ (understand data flow) → webgui/

Recommended:
  description/ (understand robot model)
  sensors/ (understand sensor data)
```

---

## 📁 Study Folder Structure

```
Study/
├── README.md                 ← You are here (index)
├── COLCON_IGNORE             ← Prevents ROS2 from building this folder
│
├── ros2/                     ← COMMON: ROS2 fundamentals
│   ├── README.md             ← ROS2 study guide overview
│   ├── 00-ros2-overview.md
│   ├── 01-workspace-and-packages.md
│   ├── 02-nodes-and-executors.md
│   ├── 03-topics-pub-sub.md
│   ├── 04-messages-interfaces.md
│   ├── 05-services.md
│   ├── 06-actions.md
│   ├── 07-parameters.md
│   ├── 08-launch-files.md
│   ├── 09-tf2-transforms.md
│   ├── 10-bag-recording.md
│   ├── 11-rviz-basics.md
│   └── 12-cli-tools.md
│
├── firmware/                 ← orbibot_rosmaster_firmware
│   └── (already complete - see firmware/README.md)
│
├── hardware/                 ← orbibot_hardware
│   └── (just completed - see hardware/README.md)
│
├── description/              ← orbibot_description (planned)
│   ├── README.md
│   ├── 00-what-is-urdf.md
│   ├── 01-urdf-basics.md
│   ├── 02-links-and-joints.md
│   ├── 03-xacro-macros.md
│   ├── 04-gazebo-simulation.md
│   ├── 05-orbibot-urdf-walkthrough.md
│   └── ...
│
├── sensors/                  ← orbibot_sensors (planned)
│   ├── README.md
│   ├── 00-sensor-types.md
│   ├── 01-lidar-laser-scan.md
│   ├── 02-camera-image-transport.md
│   ├── 03-imu-data-processing.md
│   ├── 04-sensor-fusion-basics.md
│   └── ...
│
├── localization/             ← orbibot_localization (planned)
│   ├── README.md
│   ├── 00-what-is-localization.md
│   ├── 01-odometry-fusion.md
│   ├── 02-ekf-localization.md
│   ├── 03-amcl-particle-filter.md
│   └── ...
│
├── slam/                     ← orbibot_slam (planned)
│   └── ...
│
├── navigation/               ← orbibot_navigation (planned)
│   └── ...
│
├── exploration/              ← orbibot_exploration (planned)
│   └── ...
│
├── webgui/                   ← orbibot_webgui (planned)
│   └── ...
│
└── agent/                    ← orbibot_agent (planned)
    └── ...
```

---

## 🔗 Cross-Package Dependencies

Understanding dependencies helps you choose your learning path:

```
firmware ──┐
           ├──→ hardware ──┬──→ sensors ──┬──→ localization ──┬──→ slam
ros2 ──────┤               │              │                   │
           │               │              └──→ navigation ←────┤
           │               │                   ↓              │
           │               ├──→ description ───┤              │
           │               │                   └──→ exploration
           │               │
           └──→ webgui ←───┘
           
agent ←── (uses navigation, exploration, and sensors)
```

**Key insight:** Many packages depend on `hardware/` for sensor data and `localization/` for position information.

---

## 🎓 Skill Levels

Each study guide targets specific skill levels:

| Level | Description | Example |
|-------|-------------|---------|
| **Beginner** | No prior experience with topic | Never used ROS2 before |
| **Intermediate** | Some experience, needs integration knowledge | Knows ROS2 basics, needs hardware interface specifics |
| **Advanced** | Experienced, needs OrbiBot-specific details | Knows navigation, needs OrbiBot's configuration |

Each `README.md` in package folders indicates the target level.

---

## 📝 How to Use This Documentation

### 1. Choose Your Path
- Review learning paths above
- Select based on your goals and prior experience

### 2. Follow Prerequisites
- Each package README lists required prior knowledge
- Follow the dependency chain

### 3. Active Learning
- Don't just read - run commands
- Modify code and observe changes
- Complete all exercises

### 4. Cross-Reference
- Use links between related topics
- Review earlier material when confused

### 5. Build Projects
- Apply knowledge to real tasks
- Start simple, increase complexity

---

## 🛠️ Recommended Tools

### Essential
- **VS Code** with ROS2 extension
- **Ubuntu 22.04/24.04** (ROS2 Jazzy)
- **Terminator** or **Tilix** (multi-terminal)

### Useful
- **rqt** - ROS2 GUI tools
- **RViz2** - Visualization
- **Gazebo** - Simulation
- **PlotJuggler** - Data plotting

---

## 📊 Study Time Estimates

| Package | Beginner | Intermediate | Advanced |
|---------|----------|--------------|----------|
| ros2 | 15 hrs | 8 hrs | 3 hrs |
| firmware | 30 hrs | 20 hrs | 10 hrs |
| hardware | 15 hrs | 10 hrs | 5 hrs |
| description | 10 hrs | 6 hrs | 3 hrs |
| sensors | 15 hrs | 10 hrs | 5 hrs |
| localization | 20 hrs | 12 hrs | 6 hrs |
| slam | 15 hrs | 10 hrs | 5 hrs |
| navigation | 25 hrs | 15 hrs | 8 hrs |
| exploration | 15 hrs | 10 hrs | 5 hrs |
| webgui | 20 hrs | 12 hrs | 6 hrs |
| agent | 25 hrs | 15 hrs | 8 hrs |
| **TOTAL** | **205 hrs** | **128 hrs** | **64 hrs** |

*Times assume hands-on practice, not just reading*

---

## 🚀 Quick Start

**I want to...**

| Goal | Start Here |
|------|------------|
| Learn ROS2 from scratch | [ros2/README.md](ros2/) |
| Understand OrbiBot's embedded firmware | [firmware/README.md](firmware/) |
| Understand hardware driver | [hardware/README.md](hardware/) |
| Build robot models | [description/README.md](description/) (create) |
| Work with sensors | [sensors/README.md](sensors/) (create) |
| Implement localization | [localization/README.md](localization/) (create) |
| Create maps | [slam/README.md](slam/) (create) |
| Navigate autonomously | [navigation/README.md](navigation/) (create) |
| Explore autonomously | [exploration/README.md](exploration/) (create) |
| Build web interface | [webgui/README.md](webgui/) (create) |
| Add AI capabilities | [agent/README.md](agent/) (create) |

---

## 📖 Current Status

| Package | Status | Files | Completeness |
|---------|--------|-------|--------------|
| ros2 | 🔴 Not started | 0/13 | 0% |
| firmware | 🟢 Complete | 27/27 | 90%+ |
| hardware | 🟢 Complete | 9/9 | 100% |
| description | 🔴 Not started | 0/8 | 0% |
| sensors | 🔴 Not started | 0/8 | 0% |
| localization | 🔴 Not started | 0/8 | 0% |
| slam | 🔴 Not started | 0/6 | 0% |
| navigation | 🔴 Not started | 0/10 | 0% |
| exploration | 🔴 Not started | 0/6 | 0% |
| webgui | 🔴 Not started | 0/8 | 0% |
| agent | 🔴 Not started | 0/8 | 0% |

**Legend:**
- 🟢 Complete (ready for use)
- 🟡 In progress
- 🔴 Not started

---

## 🤝 Contributing

This is a living documentation. To improve:
1. Follow the established format (small files, clear progression)
2. Cross-reference related topics
3. Include hands-on exercises
4. Test all code examples

---

## 📞 Support

If stuck:
1. Check package-specific README
2. Review prerequisite topics
3. Check issue files in source packages
4. Run diagnostic tools mentioned in debugging guides

---

**Ready to begin? Choose your starting point above! 🚀**

---

*Last Updated: March 2026*  
*Version: 1.0*  
*Total Documentation: ~50,000+ lines across all packages*