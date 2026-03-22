# OrbiBot — Test & QA Strategy

**Robot:** Mecanum-wheeled mobile robot, RPi 5, STM32F103 firmware, ROS 2 Jazzy
**Created:** 2026-03-22

> ✅ = already exists, 🔲 = proposed.

---

## Test Pyramid Overview

```
                    ┌─────────┐
                    │   E2E   │  ← Full robot bringup, SLAM loop, nav goal
                   ─┤  (few)  ├─
                  / └─────────┘ \
                 /                \
            ┌──────────────┐
            │  Integration │  ← ROS node + mock serial/topics, launch tests
           ─┤  (moderate)  ├─
          / └──────────────┘ \
         /                    \
    ┌───────────────────────┐
    │     Unit (many)       │  ← Pure logic: kinematics, PID, parsing, safety
    └───────────────────────┘
```

**নীতি:** সবচেয়ে বেশি Unit test (দ্রুত, কোনো hardware দরকার নেই), তারপর Integration, সবচেয়ে কম E2E।

---

## 1. Firmware — `orbibot_rosmaster_firmware`

### 1A. Offline Unit Tests (Python, no hardware)


| #   | Test Area                 | What to Test                                                                                                                                                                                        | Priority |
| --- | ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ✅   | Protocol packet building  | Checksum, length, all func codes                                                                                                                                                                    | Done     |
| ✅   | IMU raw parsing (18-byte) | gyro+accel+mag, short payload rejection                                                                                                                                                             | Done     |
| ✅   | Function code correctness | All codes match `protocol.h`                                                                                                                                                                        | Done     |
| 🔲  | Mecanum kinematics math   | Forward/inverse kinematics formulas (Python port) — known wheel geometry (R=50mm, lx=130mm, ly=180mm), verify FL/BL/FR/BR for pure forward, pure lateral, pure rotation, diagonal, combined motions | High     |
| 🔲  | Odometry integration math | Encoder ticks → distance → pose update (Python port) — test straight line, 90° turn, wraparound handling, float drift accumulation                                                                  | High     |
| 🔲  | PID algorithm             | Incremental PID step function (Python port) — test P-only, PI, PID, windup saturation, zero-crossing, derivative kick                                                                               | Medium   |
| 🔲  | Battery voltage encoding  | `voltage × 10 → uint8` with saturation at 255 (25.5V max)                                                                                                                                           | Low      |
| 🔲  | Odom report parsing       | 24-byte payload (6×int32 LE): x,y,theta,vx,vy,omega scale conversion                                                                                                                                | Medium   |


> **Idea:** Firmware-এর core math (kinematics, odometry, PID) C থেকে Python-এ port করে test করা যায়, কারণ সেটা STM32 ছাড়াই রান করা সম্ভব। অথবা CeedlingUnit/Unity দিয়ে native C unit test।

### 1B. Hardware Integration Tests (Python + serial, robot connected)


| #   | Test Area                  | What to Test                                                              | Priority    |
| --- | -------------------------- | ------------------------------------------------------------------------- | ----------- |
| ✅   | Connection & auto-report   | Connect, enable, receive packets                                          | Done        |
| ✅   | Encoder data               | Packet parsing, 4-motor counts                                            | Done        |
| ✅   | IMU raw + attitude         | Data reception, value sanity                                              | Done        |
| ✅   | Battery monitoring         | Voltage reading, threshold checks (4S LiFePO4)                            | Done        |
| ✅   | Data rate                  | 20Hz per type, 100 pkt/s total                                            | Done        |
| ✅   | Safety: command timeout    | 2000ms firmware timeout → motors stop                                     | Done        |
| ✅   | Safety: stop command       | Explicit stop works                                                       | Done        |
| ✅   | Buzzer                     | Beep on/off                                                               | Done        |
| ✅   | PID velocity control       | Steady-state error measurement                                            | Done        |
| 🔲  | Encoder direction          | All 4 motors: positive cmd → positive encoder delta (⚠️ FW-BUG-1 pending) | **Blocked** |
| 🔲  | Motor direction symmetry   | Send vx=+0.2 → all wheels forward, vy=+0.2 → mecanum strafe left          | High        |
| 🔲  | Odometry straight-line     | Push 1m, verify odom x ≈ 1.0m                                             | High        |
| 🔲  | Odometry rotation          | Rotate 360°, verify yaw ≈ 2π                                              | Medium      |
| 🔲  | Reset encoders             | Call reset, verify counts return to 0                                     | Medium      |
| 🔲  | Reset odometry             | Call reset, verify pose = (0,0,0)                                         | Medium      |
| 🔲  | Firmware version query     | Send 0x51, parse major.minor response                                     | Low         |
| 🔲  | Mag calibration round-trip | Set offsets → read IMU mag → verify bias shifted                          | Low         |


---

## 2. Hardware Node — `orbibot_hardware`

### 2A. Unit Tests (pytest, no ROS, mock serial)


| #   | Test Area                      | What to Test                                                                                 | Priority |
| --- | ------------------------------ | -------------------------------------------------------------------------------------------- | -------- |
| ✅   | Protocol checksum & length     | Packet build convention                                                                      | Done     |
| ✅   | Driver: protocol parsing       | `_parse_data()` for all 5 report types (speed, ICM raw 18-byte, attitude, encoder, odom)     | Done     |
| ✅   | Driver: command building       | set_pid_param, set_yaw_pid, set_car_motion, set_mag_calibration, reset_odom, reset_encoders  | Done     |
| ✅   | Driver: beep ValueError        | Negative on_time raises                                                                      | Done     |
| ✅   | Driver: mag bounds check       | ±327.67 µT overflow rejection                                                                | Done     |
| ✅   | Launch file validity           | hardware.launch.py importable, returns LaunchDescription                                     | Done     |
| 🔲  | Odometry computation           | `hardware_node._update_odometry()` — encoder delta → dx/dy/dtheta, covariance growth & decay | **High** |
| 🔲  | Odometry deduplication         | Same odom data → skip publish; heartbeat after `heartbeat_interval`                          | High     |
| 🔲  | Velocity limiting              | `cmd_vel` callback → max_velocity/max_angular clamp                                          | High     |
| 🔲  | Command timeout                | No `cmd_vel` for 2s → stop sent once, flag set                                               | High     |
| 🔲  | PID rate limiting              | Rapid PID messages → only first passes within `pid_rate_limit` window                        | Medium   |
| 🔲  | Yaw PID save key               | `_yaw_pid_save_callback` uses `'_last_yaw_pid_save_update'` key (regression)                 | Medium   |
| 🔲  | IMU soft-iron calibration      | Raw mag × soft_iron_scale → corrected output                                                 | Medium   |
| 🔲  | Battery voltage → SystemStatus | `battery_voltage / 10.0` → status message field                                              | Low      |
| 🔲  | Quaternion from yaw            | `yaw → quaternion (0,0,sin(y/2),cos(y/2))`                                                   | Low      |
| 🔲  | Joint state computation        | Encoder ticks → wheel angle (rad) via CPR                                                    | Low      |


### 2B. ROS Integration Tests (rclpy, mock serial)


| #   | Test Area                 | What to Test                                                                           | Priority |
| --- | ------------------------- | -------------------------------------------------------------------------------------- | -------- |
| 🔲  | /odom publishing          | Feed mock encoder data → verify Odometry msg on /odom (QoS: RELIABLE, TRANSIENT_LOCAL) | High     |
| 🔲  | /imu/data_raw publishing  | Feed mock ICM raw → verify Imu msg (gyro rad/s, accel m/s², no orientation)            | High     |
| 🔲  | /imu/mag publishing       | Feed mock mag → verify MagneticField msg in Tesla (skip if all-zero)                   | Medium   |
| 🔲  | /cmd_vel → serial write   | Publish Twist → verify set_car_motion() called with correct mm/s                       | High     |
| 🔲  | Service: set_motor_enable | Call service → verify serial command sent, state flag updated                          | Medium   |
| 🔲  | Service: reset_odometry   | Call → verify FUNC_RESET_ODOM sent                                                     | Medium   |
| 🔲  | Service: calibrate_imu    | Call → verify response bias_values=[0,0,0]                                             | Low      |
| 🔲  | TF: odom → base_footprint | Verify transform published with correct pose                                           | Medium   |
| 🔲  | System monitor enrichment | Feed SystemStatus → verify CPU%, RAM%, temp added                                      | Low      |


---

## 3. Sensors — `orbibot_sensors`

### 3A. Unit Tests


| #   | Test Area                           | What to Test                                                            | Priority |
| --- | ----------------------------------- | ----------------------------------------------------------------------- | -------- |
| 🔲  | Obstacle detector: sector math      | 8 sectors × 45°, angle→sector mapping, range NaN handling               | High     |
| 🔲  | Obstacle detector: hysteresis       | State transitions (clear→warning→danger→clear) with distance thresholds | Medium   |
| 🔲  | Obstacle detector: minimum distance | Per-sector min distance from LaserScan ranges array                     | Medium   |


### 3B. Launch Tests


| #   | Test Area         | What to Test                                                    | Priority |
| --- | ----------------- | --------------------------------------------------------------- | -------- |
| 🔲  | lidar.launch.py   | Importable, correct rplidar parameters (scan_mode, serial_port) | Medium   |
| 🔲  | camera.launch.py  | Importable, correct RealSense parameters                        | Medium   |
| 🔲  | sensors.launch.py | Importable, composition of lidar + camera + obstacle detector   | Low      |


---

## 4. Teleop — `orbibot_teleop`

### 4A. Unit Tests


| #   | Test Area              | What to Test                                                                 | Priority |
| --- | ---------------------- | ---------------------------------------------------------------------------- | -------- |
| 🔲  | Deadzone filtering     | Stick values below 8% → 0; above 8% → scaled linearly                        | High     |
| 🔲  | Velocity clamping      | max_linear=1.0 m/s, max_angular=2.0 rad/s — clamp both positive and negative | High     |
| 🔲  | Mecanum mode selection | 7 modes: button → mode enum, mode → axis mapping                             | Medium   |
| 🔲  | Joy → Twist conversion | Stick axes + mode → correct vx, vy, wz                                       | Medium   |
| 🔲  | Mode display string    | Each MecanumMode has human-readable name                                     | Low      |


---

## 5. Localization — `orbibot_localization`

### 5A. Unit Tests


| #   | Test Area                  | What to Test                                            | Priority |
| --- | -------------------------- | ------------------------------------------------------- | -------- |
| 🔲  | Hard-iron bias calculation | `(min+max)/2` for 3 axes — test with known data set     | High     |
| 🔲  | Soft-iron scale estimation | Ellipsoid → sphere normalization (requires numpy)       | Medium   |
| 🔲  | Zero-sample skipping       | Skip (0,0,0) mag readings from calibration dataset      | Medium   |
| 🔲  | Min sample requirement     | At least N samples before valid calibration (e.g., 100) | Low      |


### 5B. Launch Tests


| #   | Test Area              | What to Test                                                    | Priority |
| --- | ---------------------- | --------------------------------------------------------------- | -------- |
| 🔲  | localization.launch.py | EKF node starts, loads ekf_params.yaml, correct topic remapping | Medium   |
| 🔲  | EKF config validation  | odom0_config positions=false, imu0_config yaw+yaw_dot=true      | Medium   |


---

## 6. Exploration — `orbibot_exploration`

### 6A. Unit Tests (pure logic, no ROS)


| #   | Test Area                 | What to Test                                              | Priority |
| --- | ------------------------- | --------------------------------------------------------- | -------- |
| 🔲  | BFS frontier detection    | Known occupancy grid → correct frontier cells found       | **High** |
| 🔲  | 4-connected neighbors     | Edge cells, corner cells, out-of-bounds rejection         | High     |
| 🔲  | 8-connected neighbors     | Same edge cases with diagonal neighbors                   | Medium   |
| 🔲  | Frontier clustering       | Adjacent frontier cells → grouped into Frontier objects   | Medium   |
| 🔲  | Frontier cost calculation | Distance + information gain heuristic                     | Medium   |
| 🔲  | Best frontier selection   | Lowest cost frontier selected; blacklist filtering        | Medium   |
| 🔲  | Frontier blacklisting     | Unreachable frontier added to blacklist; blacklist expiry | Low      |


### 6B. Integration Tests


| #   | Test Area              | What to Test                                              | Priority |
| --- | ---------------------- | --------------------------------------------------------- | -------- |
| 🔲  | /map → frontier update | Publish OccupancyGrid → verify frontiers detected         | Medium   |
| 🔲  | Command interface      | Publish "start"/"stop"/"pause" → verify state transitions | Medium   |


---

## 7. Navigation — `orbibot_navigation`

### 7A. Launch Tests


| #   | Test Area              | What to Test                                                                      | Priority |
| --- | ---------------------- | --------------------------------------------------------------------------------- | -------- |
| 🔲  | navigation.launch.py   | Importable, loads nav2_params.yaml                                                | Medium   |
| 🔲  | Nav2 params validation | MPPI + Omni model, NavfnPlanner + A*, AMCL OmniMotionModel                        | Medium   |
| 🔲  | Velocity chain config  | controller(cmd_vel_nav) → smoother(cmd_vel_smoothed) → collision_monitor(cmd_vel) | Low      |


---

## 8. Description — `orbibot_description`

### 8A. URDF/Xacro Tests


| #   | Test Area             | What to Test                                                                            | Priority |
| --- | --------------------- | --------------------------------------------------------------------------------------- | -------- |
| 🔲  | Xacro expansion       | `orbibot.urdf.xacro` expands without errors                                             | High     |
| 🔲  | Link count            | Expected links: base_footprint, base_link, 4 wheels, lidar, camera, imu                 | High     |
| 🔲  | Joint count           | Expected joints: base_joint (fixed), 4 wheel joints (continuous), sensor joints (fixed) | High     |
| 🔲  | Wheel radius property | Matches hardware spec (0.05m)                                                           | Medium   |
| 🔲  | Track width property  | Matches hardware spec (0.36m left-right)                                                | Medium   |
| 🔲  | Wheelbase property    | Matches hardware spec (0.26m front-rear)                                                | Medium   |
| 🔲  | TF chain validation   | base_footprint → base_link → [wheel_links, sensor_links]                                | Medium   |
| 🔲  | Inertia non-zero      | All links with mass > 0 have non-zero inertia tensor                                    | Low      |
| 🔲  | Collision geometry    | All links with visual have matching collision                                           | Low      |


---

## 9. Bringup — `orbibot_bringup`

### 9A. Launch Tests


| #   | Test Area             | What to Test                                                         | Priority |
| --- | --------------------- | -------------------------------------------------------------------- | -------- |
| 🔲  | robot.launch.py       | Importable, includes description + hardware + sensors + localization | High     |
| 🔲  | mapping.launch.py     | Importable, includes slam_toolbox                                    | Medium   |
| 🔲  | exploration.launch.py | Importable, includes exploration + navigation                        | Medium   |


---

## 10. Messages — `orbibot_msgs`

### 10A. Interface Tests


| #   | Test Area        | What to Test                                        | Priority |
| --- | ---------------- | --------------------------------------------------- | -------- |
| 🔲  | SystemStatus.msg | Instantiate, set fields, serialize/deserialize      | Medium   |
| 🔲  | SafetyStatus.msg | Same                                                | Medium   |
| 🔲  | All .srv files   | Request/response instantiation, field types correct | Medium   |


---

## 11. AI Agent — `orbibot_agent`

### 11A. Unit Tests (pure Python, no ROS, no API calls)


| #   | Test Area                          | What to Test                                                       | Priority |
| --- | ---------------------------------- | ------------------------------------------------------------------ | -------- |
| 🔲  | SafetyManager: velocity validation | vx clamped to ±max_linear, wz to ±max_angular                      | **High** |
| 🔲  | SafetyManager: duration validation | Duration clamped to [0.1, 10.0]s                                   | High     |
| 🔲  | SafetyManager: emergency stop flag | Flag set/clear, blocks motion when active                          | High     |
| 🔲  | Tool registry: schema generation   | All 8 tools have valid JSON schema (name, description, parameters) | High     |
| 🔲  | Tool registry: tool lookup         | `execute_tool("move_robot", {...})` finds correct handler          | Medium   |
| 🔲  | Tool registry: unknown tool        | Returns error for non-existent tool name                           | Medium   |
| 🔲  | env_loader: .env.local parsing     | `KEY=value`, `KEY="quoted"`, comments, empty lines                 | Medium   |
| 🔲  | env_loader: candidate paths        | Searches package dir, workspace root, home dir                     | Medium   |
| 🔲  | Config loading                     | agent_params.yaml → correct default provider, safety limits        | Medium   |
| 🔲  | System prompt loading              | Template file loaded, variables substituted                        | Low      |


### 11B. Unit Tests (mock LLM API, no real calls)


| #   | Test Area                          | What to Test                                                          | Priority |
| --- | ---------------------------------- | --------------------------------------------------------------------- | -------- |
| 🔲  | Gemini provider: init              | API key from env, model name correct                                  | High     |
| 🔲  | Gemini provider: tool calling      | Mock response with tool_call → tool executed → result returned to LLM | High     |
| 🔲  | Anthropic provider: tool calling   | Same flow with Claude tool_use format                                 | Medium   |
| 🔲  | Ollama provider: local model check | Endpoint health check, model availability                             | Medium   |
| 🔲  | Provider fallback                  | Primary provider fails → fallback to secondary                        | Low      |


### 11C. Integration Tests (mock ROS bridge)


| #   | Test Area             | What to Test                                                         | Priority |
| --- | --------------------- | -------------------------------------------------------------------- | -------- |
| 🔲  | move_robot tool       | `{"vx": 0.3, "duration": 2.0}` → cmd_vel published, safety validated | High     |
| 🔲  | stop_robot tool       | Emergency stop → zero velocity published                             | High     |
| 🔲  | get_battery tool      | Returns current battery voltage from cached /system_status           | Medium   |
| 🔲  | get_sensor_data tool  | Returns latest IMU/odom from cached subscriptions                    | Medium   |
| 🔲  | set_motor_enable tool | Calls /orbibot/set_motor_enable service                              | Medium   |


### 11D. HTTP API Tests (mock server, no LLM)


| #   | Test Area              | What to Test                            | Priority |
| --- | ---------------------- | --------------------------------------- | -------- |
| 🔲  | POST /api/chat         | Valid message → 200, streaming response | Medium   |
| 🔲  | POST /api/chat (empty) | Empty message → 400                     | Medium   |
| 🔲  | POST /api/reset        | Session cleared → 200                   | Low      |
| 🔲  | GET /api/health        | Returns `{"status": "ok"}`              | Low      |
| 🔲  | GET /api/providers     | Returns available provider list         | Low      |


---

## 12. Web GUI — `orbibot_webgui`

### 12A. Unit Tests


| #   | Test Area                    | What to Test                                     | Priority |
| --- | ---------------------------- | ------------------------------------------------ | -------- |
| 🔲  | FrameBuffer: thread safety   | Concurrent update + get → no data corruption     | Medium   |
| 🔲  | FrameBuffer: freshness check | Age-based `is_fresh()` with configurable timeout | Medium   |
| 🔲  | Image encoding               | cv2 frame → JPEG bytes → correct header          | Low      |


### 12B. Launch Tests


| #   | Test Area        | What to Test                         | Priority |
| --- | ---------------- | ------------------------------------ | -------- |
| 🔲  | webgui.launch.py | Importable, correct HTTP port config | Low      |


---

## 13. Cross-Package Integration Tests

এগুলো একাধিক package একসাথে কাজ করে কিনা পরীক্ষা করে।


| #   | Pipeline                  | Test Description                                                                                            | Priority |
| --- | ------------------------- | ----------------------------------------------------------------------------------------------------------- | -------- |
| 🔲  | Firmware ↔ Hardware Node  | Mock serial stream → verify /odom, /imu/data_raw, /imu/mag, /orbibot/encoders published with correct values | **High** |
| 🔲  | cmd_vel → Firmware        | Publish Twist on /cmd_vel → verify correct MOTION packet sent on serial                                     | High     |
| 🔲  | Hardware → EKF            | Mock /odom (velocity) + /imu/data → verify /odometry/filtered output                                        | Medium   |
| 🔲  | LiDAR → Obstacle Detector | Mock /scan with known obstacle → verify obstacle detected in correct sector                                 | Medium   |
| 🔲  | Agent → Robot Motion      | Chat "move forward" → LLM tool call → cmd_vel published (full loop with mock LLM)                           | Medium   |
| 🔲  | TF Tree Completeness      | With robot.launch.py → verify full TF chain: map→odom→base_footprint→base_link→sensors                      | Medium   |
| 🔲  | SLAM Pipeline             | Mock /scan + /odometry/filtered → verify /map published (requires slam_toolbox)                             | Low      |


---

## 14. End-to-End System Tests

এগুলো real hardware অথবা simulation-এ চলবে। সবচেয়ে কম সংখ্যক কিন্তু সবচেয়ে valuable।


| #   | Test                     | What to Verify                                                                  | Requires       |
| --- | ------------------------ | ------------------------------------------------------------------------------- | -------------- |
| 🔲  | Robot bringup smoke test | `robot.launch.py` → all nodes alive, /odom publishing, TF tree valid within 30s | Hardware       |
| 🔲  | Teleop drive test        | Joystick forward command → robot moves, odom distance > 0                       | Hardware       |
| 🔲  | Straight-line accuracy   | Drive 1m forward → odom reports 1.0m ± 5%                                       | Hardware       |
| 🔲  | Rotation accuracy        | Rotate 360° → yaw returns to ±5° of start                                       | Hardware       |
| 🔲  | SLAM map building        | Drive around room → map saved with walls/doors visible                          | Hardware       |
| 🔲  | Nav2 goal reached        | Send nav goal 2m away → robot navigates, `goal_reached` status                  | Hardware + Map |
| 🔲  | Emergency stop response  | E-stop triggered → all motors stop within 100ms                                 | Hardware       |
| 🔲  | Battery low response     | Simulate low voltage → warning beep + motor disable at critical                 | Hardware       |


---

## Priority Summary


| Priority    | Count     | Focus                                                                    |
| ----------- | --------- | ------------------------------------------------------------------------ |
| **High**    | ~30 tests | Core safety, protocol correctness, kinematics math, ROS topic publishing |
| **Medium**  | ~35 tests | Integration flows, config validation, secondary features                 |
| **Low**     | ~20 tests | Edge cases, UI, documentation tests                                      |
| **Blocked** | 1 test    | Encoder direction (needs hardware — FW-BUG-1)                            |


### কোথা থেকে শুরু করা উচিত? (Recommended Order)

1. **Hardware Node unit tests** — odometry, velocity limiting, timeout, deduplication (সবচেয়ে critical, কারণ এটা সব package-এর ভিত্তি)
2. **AI Agent safety + tool tests** — velocity validation, tool registry, mock LLM (user-facing safety)
3. **Exploration frontier detection** — BFS algorithm pure unit tests (complex logic, easy to test offline)
4. **Teleop deadzone + clamping** — simple but important for hardware safety
5. **URDF/Xacro validation** — link/joint count, wheel geometry matches config
6. **Cross-package: firmware ↔ hardware node** — mock serial → ROS topics (highest integration value)
7. **Launch file validation** — all packages' launch files importable

---

## Test Infrastructure Notes

### Tools

- **pytest** — all Python unit + integration tests
- **launch_testing** — ROS 2 launch tests (E2E)
- **unittest.mock** — serial port, ROS topics, LLM APIs
- **colcon test** — CI integration

### Running Tests

```bash
# All offline tests (no hardware)
python3 -m pytest src/orbibot_rosmaster_firmware/tests/test_protocol_commands.py -v
python3 -m pytest src/orbibot_hardware/test/ -v

# Hardware integration tests (robot connected)
cd src/orbibot_rosmaster_firmware/tests && python3 run_all_tests.py --port /dev/motordriver

# ROS integration tests (after colcon build)
colcon test --packages-select orbibot_hardware
colcon test-result --verbose
```

### CI/CD Considerations

- Offline unit tests → GitHub Actions (no hardware)
- Hardware integration tests → manual (robot connected)
- E2E tests → manual (full robot bringup)

---

*Last updated: 2026-03-22*