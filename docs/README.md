# OrbiBot V1 documentation

The code is the source of truth: when a page disagrees with the code, the page
is wrong. Each package documents itself beside its code; this folder holds what
belongs to the robot as a whole.

## Start here

| Page | What it covers |
|---|---|
| [Getting started](getting-started.md) | Setting up the Pi, the firmware and a first launch |
| [Running the robot](operations/running.md) | Launch recipes: the base, the dashboard, mapping, navigation, exploration, the agent |
| [Status](status.md) | What was built, what was tested and how, and the known limits |
| [Packages](packages.md) | The 13 packages, with links to each one's README |

## How it works

| Page | What it covers |
|---|---|
| [System overview](architecture/system-overview.md) | The two-computer split, the data flow, the estimation chain and the frames |
| [Command pipeline](architecture/command-pipeline.md) | How velocity commands should reach the wheels (designed, not built) |
| [Dashboard design](architecture/dashboard-design.md) | A cheaper data path for the web dashboard (designed, not built) |
| [Hardware](hardware/README.md) | What is on the robot, measured, and the parts list |
| [ROSMaster board](hardware/rosmaster-board.md) | The motor board's pins, timers and power |

## Working on it

| Page | What it covers |
|---|---|
| [Testing guide](testing/README.md) | Test procedures and what each step should show |
| [Baseline run, 2026-03-14](testing/2026-03-14-baseline.md) | An early full-system run, kept as a record |
| [PID tuning](operations/pid-tuning.md) | Tuning the wheel and yaw PIDs from the dashboard |
| [Troubleshooting](operations/troubleshooting.md) | The first checks when something doesn't work |

## Learning from it

[The lessons](learn/README.md): 70 lessons in six areas (ROS 2, firmware,
the hardware bridge, the robot model, localisation and sensors), built on
this robot's code.

## Other robots

Robots whose designs were compared with OrbiBot's:
[Yahboom ROSMaster X3](reference/yahboom-rosmaster-x3.md), the source of the
serial protocol and driver;
[LGDXRobot2](reference/lgdxrobot2.md) and its
[ChassisTuner](reference/lgdxrobot2-chassistuner.md); and
[AuBot](reference/aubot.md).

## Inside each package

```
src/<package>/README.md          topics, services, parameters, launch files
src/<package>/CHANGELOG.md       what changed and why (where kept)
src/<package>/known-issues.md    what is open
src/orbibot_rosmaster_firmware/test-report.md   what was tested on the hardware, and when
```

`docs/COLCON_IGNORE` keeps colcon out of this folder.
