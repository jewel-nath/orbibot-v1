# PID tuning

How to check that the wheel speed control works, and how to find better PID
gains, with the web dashboard's **Diagnostics → PID Response Graph**.

**Do the final tuning with the robot on the floor.** With the wheels in the
air there is no load, so gains found that way are only a starting point.

## 1. Check that everything works

### Data and topics

| Check | How |
|---|---|
| `/odom` is published | `ros2 topic hz /odom`: about 20 Hz while the robot moves, and a 0.5 s heartbeat when it stands still |
| The dashboard reads wheel odometry | Settings → ROS Topics → Odometry topic = `/odom`. Tune on wheel odometry, not on the EKF's output |
| The robot gets commands | It moves when you press **Send**; if not, `ros2 topic echo /cmd_vel` shows whether a Twist goes out |

### Hardware and firmware

| Check | How |
|---|---|
| Motors on | The sidebar shows Motors ON; turn them on if not |
| Encoders count | The FL, BL, FR and BR counts change when the wheels turn |
| Battery | Below the firmware's cut-off the motors are locked, so keep the voltage up |

### Reading the graph

The graph plots the target against the measured speed for Vx, Vy and Wz.
Example: with only Vx = 0.2 m/s commanded, a run showed:

| Axis | Result | Meaning |
|---|---|---|
| Vx | About 21.5 % overshoot, then oscillation | The wheel PID is a little aggressive: lower Kp or raise Kd |
| Vy | Target 0, small oscillation (MAE 0.0056) | Some cross-coupling and slip is normal when only Vx is commanded |
| Wz | Target 0, oscillation (MAE 0.013) | The heading drifts or wobbles while driving straight: tune the yaw PID |

If you see the target and the measured line, the pipeline works, and the rest
is choosing gains.

## 2. Finding better gains

There are two PIDs:

- **Motor PID** (Diagnostics → PID Tuning): how each wheel tracks its target
  speed. One set of Kp, Ki and Kd for all four wheels.
- **Yaw PID**: holds the heading while driving straight, using the IMU.

Firmware defaults: motor Kp 0.8, Ki 0.06, Kd 0.5; yaw Kp 0.4, Ki 0, Kd 0.1.

### Step 1: test one axis (Vx)

1. In **PID Response Graph**, set **Vx = 0.2**, Vy = 0, Wz = 0.
2. Press **Send** and let it record for 8 s (or press **Stop** earlier).
3. Look at the Vx graph:
   - **Large overshoot** (20 % or more): lower the motor Kp a little (0.8 →
     0.6), or raise Kd (0.5 → 0.7).
   - **Slow response, or a steady error**: raise Kp; if needed, raise Ki a
     little.
   - **Jitter or noise**: lower Kd.

### Step 2: apply and save the motor PID

- Enter the new values in **Diagnostics → PID Tuning**.
- **Apply** sets them in RAM (lost on reboot); **Flash** saves them in flash.
  Keeping gains in flash across a reboot has not been tested yet.
- After each change, run the Vx test again.

### Step 3: bring Vy and Wz towards zero

- While driving on Vx only, the closer Vy and Wz stay to 0, the better.
- **Vy oscillates:** the sideways motion comes from the same motor PID, so it
  improves as the motor PID does. If the wheels on one side behave
  differently, check those motors and encoders.
- **Wz oscillates:** tune the **yaw PID** (Diagnostics → PID Tuning → Yaw).
  A lower Kp makes the heading correction softer; a higher Kd can damp the
  oscillation.

### Step 4: test sideways and turning on their own

- **Sideways:** Vx = 0, Vy = 0.15, Wz = 0.
- **Turning:** Vx = 0, Vy = 0, Wz = 0.5. Both the yaw PID and the motor PID
  matter here.

### Symptoms and fixes

| Symptom | Try |
|---|---|
| Overshoot, oscillation | Lower Kp, raise Kd |
| Slow response | Raise Kp |
| Steady error | Raise Ki a little |
| Jitter, noise | Lower Kd |
| Turns while it should drive straight (Wz) | Tune the yaw PID (Kp, Kd) |

## 3. Letting the agent help

With the agent running (`orbibot_agent`), you can ask it to tune the PID. It
can set gains (`set_motor_pid`, `set_yaw_pid`), drive a test (`move_robot`),
record the response (`record_timeseries`) and compare runs
(`compute_statistics`), then try new gains. It sets gains in RAM only: save
the ones you like with **Flash** in the dashboard, or with `save_motor_pid`
and `save_yaw_pid`.

## See also

- [The firmware README](../../src/orbibot_rosmaster_firmware/README.md) and
  `include/orbibot_config.h`, for the PID in the firmware
- [The web dashboard README](../../src/orbibot_webgui/README.md), for the
  `/orbibot/pid_params`, `/orbibot/yaw_pid_params` and `/orbibot/pid_save` topics
- [The testing guide](../testing/README.md), section 3, for tuning from the
  command line
