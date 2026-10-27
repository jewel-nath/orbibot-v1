# Status

Where OrbiBot V1 stands: what was built, what was tested and how, and what
is known to be wrong. A package's own open issues are in its
`src/<package>/known-issues.md`; this page holds the ones that belong to no
single package.

## What was built

V1 is **built**: a welded stainless-steel mecanum robot with a Raspberry Pi 5
running ROS 2 Jazzy, and an STM32 motor board running its own firmware.

| | Status |
|---|---|
| Frame, motors, wheels, wiring | Built (from June 2025) |
| STM32 firmware: PID, encoders, IMU, odometry, protocol, safety timeout | Built; tested on the bench |
| ROS 2 bridge (`orbibot_hardware`) | Used on the robot |
| Robot model, EKF localisation | Used on the robot; the EKF was tuned in March 2026, before the IMU fixes, and needs tuning again |
| SLAM mapping with slam_toolbox | Used on the robot: maps built while driving (from July 2025) |
| Localising and driving on a saved map | Used on the robot (January 2026) |
| Nav2 navigation | Set up and run in a small room (March 2026); nothing measured |
| Frontier exploration | Written, not tested against a tuned Nav2 |
| Web dashboard | Used on the robot: driving, live camera, live map (February 2026) |
| AI agent, 58 tools | Runs on the robot; behind the dashboard's chat panel |
| Gamepad driving (`orbibot_teleop`) | Used in 2025; switched off since the dashboard |
| Command arbitration (`twist_mux`) | Designed, not built ([design](architecture/command-pipeline.md)) |
| Cheaper dashboard data path | Designed, not built ([design](architecture/dashboard-design.md)) |

## What was tested, and how

All the motion numbers below were measured **on the bench, with the wheels
off the ground**. They prove directions, signs and the safety behaviour; they
can't prove distance, drift or traction. The full results are in the
[firmware test report](../src/orbibot_rosmaster_firmware/test-report.md).

| Test | Result | Date |
|---|---|---|
| Serial protocol: round trips, malformed input, commands at a 500 Hz target (328 Hz reached) for 3.3 s | No corrupt frames, no drops | 2026-04-19 |
| Mecanum kinematics: forward, back, sideways, turning | All four wheel directions right | 2026-04-19 |
| Command timeout (2 s configured) | Motors stopped 2.12 s after the last command | 2026-04-19 |
| Velocity tracking at 150 mm/s and 700 mrad/s | Forward −1 %, back +3 %, turning +4 %, sideways −9 % (136 of 150 mm/s) | 2026-04-19 |
| Velocity clamp | Peak 1023 mm/s on a 3000 mm/s command | 2026-04-19 |
| Per-motor speed at the 1.0 m/s limit | 1001.7 to 1002.5 mm/s, 0.1 % apart | 2026-04-28 |
| Accelerometer, robot level and still | \|a\| = 9.802 m/s², 0.9995 of g | 2026-08-03 |
| ROS 2 end to end, robot still | `/imu/data_raw`, `/joint_states`, `/orbibot/encoders` at about 50 Hz | 2026-08-03 |
| IMU noise, robot still | Per-axis covariances, 212 samples (before the IMU fixes; to measure again) | 2026-03-24 |

**Not measured yet:** anything with the robot driving on the floor (distance,
drift, traction, PID under load), keeping PID gains in flash across a reboot,
and long or hot running.

## Known limits

### Four publishers on `/cmd_vel`, and nothing chooses between them (high)

`orbibot_hardware` subscribes to `/cmd_vel`, and four things publish to it:

| Publisher | Where |
|---|---|
| Web dashboard | `orbibot_webgui` frontend, through rosbridge |
| AI agent | `orbibot_agent/core/ros_bridge/motion.py` |
| Gamepad | `orbibot_teleop/controller.py` (switched off, but wired) |
| Nav2 | `collision_monitor` output |

There is no `twist_mux` in the workspace, so the last writer wins: a Nav2 goal
and the dashboard's joystick can fight mid-drive, with no priority. The fix is
designed in [the command pipeline](architecture/command-pipeline.md).

### Accelerometer X and Y scale not confirmed while moving (medium)

The Z-axis fix of 2026-08-03 was checked with the robot still. X and Y read
about zero when the robot is still either way, so their scale, the axes a
ground robot actually accelerates along, needs a known acceleration with the
robot on the ground.

### Localisation figures from before 2026-08-03 are suspect (medium)

Two faults fed the estimator bad data for months: the accelerometer read too
high on Z, and the raw IMU packets were silently dropped by a length check
whenever the firmware and the driver were out of step. Any tuning result,
drift figure or EKF covariance recorded before 2026-08-03 was measured through
that, and should be measured again rather than trusted.

### No absolute heading

The magnetometer was removed on 2026-04-28, so yaw comes from the gyro alone
and drifts. SLAM or AMCL correct it through `map → odom`. How fast it drifts
has not been measured.

### Other numbers to treat with care

- The top speed of about 1.74 m/s is worked out from the motor datasheet, not
  measured. The firmware limits the robot to 1.0 m/s.
- On the bench, the back-right motor (M4) counted about 12–15 % fewer encoder
  ticks than the others in one test (see the test report, §6).
- Nav2's speed limits, footprint and inflation were never measured. Its
  350 × 250 mm footprint is the frame; the wheel centres are 360 mm apart, so
  the wheels stick out of it.
