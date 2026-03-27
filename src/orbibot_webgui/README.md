# OrbiBot Web GUI

Browser-based dashboard for real-time monitoring, manual control, autonomous navigation,
and AI-assisted interaction with the OrbiBot mecanum-wheeled mobile robot.

---

## Overview

The web GUI is a full-stack ROS 2 component that runs alongside the robot stack.
It gives any device with a browser a live view of the robot — no ROS installation needed
on the client side.

| Layer | Technology | Role |
|-------|-----------|------|
| Frontend | React 19 + TypeScript + Vite | Dashboard UI |
| ROS bridge | rosbridge_suite (WebSocket) | Bi-directional ROS ↔ browser |
| Video bridge | aiortc WebRTC server | Low-latency camera streaming |
| AI backend | orbibot_agent chat_server | LLM-based robot interaction |

The GUI is a pure observer and commander: it **never drives hardware directly** — all
commands go through standard ROS 2 topics and services.

---

## System Architecture

```
Browser
├── React App (http://robot:5173)
│   ├── roslib (WebSocket)  ──────────►  rosbridge_server :9090  ──►  ROS 2 topics/services
│   ├── RTCPeerConnection   ──────────►  WebRTC server    :8081  ──►  /camera/color/image_raw
│   └── fetch (HTTP)        ──────────►  chat_server      :8082  ──►  orbibot_agent
│
└── Mobile controller page (http://robot:5173/controller)
```

### Provider stack (App.tsx)

```
SettingsProvider        — persists all config to localStorage
  ThemeProvider         — dark/light mode (next-themes)
    PathProvider        — client-side routing (dashboard / diagnostics)
      RosProvider       — rosbridge WebSocket + reconnect
        WebRTCProvider  — WebRTC stream lifecycle
          NavigationProvider  — waypoints, nav status, path display
            AppContent
```

---

## Data Flow

### ROS → Browser (telemetry)

```
/orbibot/system_status          ──► Battery gauge, motor status
/orbibot/system_status_enriched ──► CPU, RAM, temperature, disk
/orbibot/safety_status          ──► E-stop, fault, cmd-timeout flags
/orbibot/encoders               ──► Encoder counts per wheel (FL/BL/FR/BR)
/odom                           ──► Raw wheel odometry
/odometry/filtered              ──► EKF-fused odometry
/imu/data                       ──► IMU orientation + angular velocity (filtered)
/imu/data_raw                   ──► Raw IMU (gyro + accel)
/imu/mag                        ──► Magnetometer field
/joint_states                   ──► Per-wheel velocity (rad/s), position (rad)
/scan                           ──► LiDAR 2D scan
/map                            ──► SLAM occupancy grid
/plan                           ──► Nav2 planned path overlay
/navigate_to_pose/_action/status ──► Goal tracking (navigating/succeeded/failed)
/orbibot/exploration/status     ──► Exploration state
/orbibot/exploration/frontiers  ──► Live frontier markers
/diagnostics                    ──► ROS diagnostic array (IMU/Motors/LiDAR)
```

### Browser → ROS (commands)

```
/cmd_vel                      ◄── Directional buttons, joystick, keyboard
/initialpose                  ◄── Init Pose mode (map click+drag)
/goal_pose                    ◄── Navigation Goal mode (map click+drag)
/orbibot/pid_params           ◄── Motor PID gains (Apply)
/orbibot/pid_save             ◄── Motor PID to flash (Flash)
/orbibot/yaw_pid_params       ◄── Yaw PID gains
/orbibot/yaw_pid_save         ◄── Yaw PID to flash
/orbibot/beep                 ◄── Buzzer test (200 ms pulse)
/orbibot/exploration/command  ◄── start / pause / stop
```

### Services called (frontend)

```
/orbibot/get_firmware_version  ◄── Read STM32 firmware version string
/orbibot/set_motor_enable      ◄── Enable / disable motors
/orbibot/calibrate_imu         ◄── Magnetometer calibration
/orbibot/reset_encoders        ◄── Zero encoder counts
/orbibot/reset_odometry        ◄── Zero odometry pose
/navigate_to_pose/_action/cancel_goal ◄── Cancel Nav2 goal
/map_saver/save_map            ◄── Save SLAM map to disk
```

### WebRTC pipeline

```
ROS 2 /camera/color/image_raw
  → cv_bridge (ROS Image → OpenCV BGR)
  → WebRTC server FrameBuffer (thread-safe)
  → RTCPeerConnection video track
  → <video> element in CameraFeed component
Latency: ~50–100 ms on local WiFi
```

### AI chat pipeline

```
User types message → useChat hook
  → POST /api/chat/stream (SSE)        (primary)
  → POST /api/chat           (fallback blocking)
  ← streaming text chunks + tool events
  → orbibot_agent → LLM → ROS 2 tool calls → reply
```

---

## Features

### Monitoring
- Battery gauge (4S LiFePO4 thresholds: full 14.6 V → critical 10.5 V)
- System health: CPU%, RAM%, temperature, disk
- Motors ON/OFF badge + encoder counts (FL / BL / FR / BR)
- Odometry (position x/y/θ, velocity Vx/Vy/Wz); configurable topic
- IMU orientation (roll/pitch/yaw °) and angular velocity
- LiDAR 2D scan with pan/zoom
- SLAM map with robot pose overlay, track-up mode, fit-to-canvas
- Safety status: E-stop, command timeout, low battery, fault flags

### Control
- **Button mode** — 11-button mecanum grid (8 directions + 2 rotation + stop)
- **Joystick mode** — dual virtual joystick (movement + rotation); touch-friendly
- **Keyboard** — WASD / Arrow keys / QE rotation / 1–9 speed / Space·Esc stop
- Speed slider (10–100 %)
- Emergency stop button (always visible)
- PID tuning sliders on Diagnostics page (Apply / Flash to motor flash)

### Navigation
- Init Pose placement (click+drag on map → `/initialpose`)
- Navigation Goal placement (click+drag on map → `/goal_pose`)
- Goal status indicator (navigating / succeeded / failed / canceled)
- Waypoint manager: add, rename, reorder (drag-and-drop), delete, import/export JSON
- Patrol routes: sequential waypoint navigation with loop toggle and pause/resume
- Planned path overlay from Nav2 `/plan` topic

### Exploration
- Start / Pause / Stop frontier exploration
- Live frontier count
- Save SLAM map via `nav2_map_server`

### AI Chat
- Natural language robot control via `orbibot_agent`
- SSE streaming with live tool-call badges
- Provider selector: Gemini, Claude, Kimi, Ollama
- Quick-action buttons (battery, position, IMU, status, health, diagnostics)
- Markdown rendering (tables, code blocks, lists)
- Cancel generation mid-stream
- Timestamps on each message
- Multi-line input (Shift+Enter for newline, Enter to send)
- Online/offline indicator with retry

### Diagnostics page (`/diagnostics`)

Tab-based comprehensive testing, analysis, calibration, and tuning workbench:

| Tab | Contents |
|-----|----------|
| **Overview** | Safety status, firmware version, motor enable/buzzer test, battery voltage chart (5 min), connection health table (topic Hz + staleness) |
| **Motors** | Per-motor encoder counts, velocity (rad/s), position; 4-channel wheel velocity time-series; commanded vs actual Vx/Vy charts |
| **Odometry** | XY path trace (raw dashed / filtered solid), 3-channel Vx/Vy/Wz comparison chart |
| **IMU** | Attitude indicator, compass rose, 3-channel gyro + accel time-series (30 s), magnetometer XY scatter with circle-fit overlay, IMU calibration |
| **PID Tuning** | Motor PID sliders (Apply / Flash), yaw PID sliders, PID response graph (8 s record) |
| **Tools** | LiDAR scan view + statistics, data export recorder (CSV), 3-step wheel calibration wizard |

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| ROS 2 | Jazzy Jalisco |
| Node.js | 18 or later |
| Python | 3.10 or later |

```bash
# ROS packages
sudo apt install ros-jazzy-rosbridge-suite ros-jazzy-cv-bridge

# For navigation features
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup

# Python packages for WebRTC server
pip3 install aiortc aiohttp aiohttp-cors av opencv-python
```

---

## Installation

```bash
# 1. Build the ROS 2 package
cd ~/orbibot_ws
colcon build --packages-select orbibot_webgui
source install/setup.bash

# 2. Install frontend dependencies
cd src/orbibot_webgui/frontend
npm install
```

---

## Running

### Step 1 — Start ROS 2 services

```bash
# rosbridge + WebRTC server
ros2 launch orbibot_webgui webgui.launch.py

# Without camera streaming
ros2 launch orbibot_webgui webgui.launch.py use_video:=false
```

### Step 2 — Start the robot stack

```bash
ros2 launch orbibot_bringup robot.launch.py      # hardware + sensors + EKF
ros2 launch orbibot_navigation navigation.launch.py  # Nav2 (optional)
ros2 launch orbibot_exploration exploration.launch.py  # frontier exploration (optional)
ros2 launch orbibot_agent chat_server.launch.py  # AI chat (optional)
```

### Step 3 — Start the frontend

**Development (with mock data):**
```bash
cd src/orbibot_webgui/frontend
npm run dev
# Open http://localhost:5173

# Optional: run demo robot for mock ROS data
node scripts/demo-robot.js
```

**Production:**
```bash
cd src/orbibot_webgui/frontend
npm run build
# Serve frontend/dist/ with any static file server
python3 -m http.server 5173 --directory dist
```

### Mobile controller

Navigate to `http://robot_ip:5173/controller` on a phone or tablet for a full-screen
touch joystick interface.

---

## Configuration

### Settings panel (in-app)

Click the ⚙ icon in the top-right corner to configure:

| Setting | Default | Notes |
|---------|---------|-------|
| WebSocket URL | `ws://hostname:9090` | Requires page reload to reconnect |
| WebRTC Server | `http://hostname:8081` | Camera streaming |
| Chat API Server | `http://hostname:8082` | orbibot_agent chat_server |
| Max Linear Velocity | 1.0 m/s | Slider upper bound |
| Max Angular Velocity | 2.0 rad/s | Slider upper bound |
| LiDAR Scan topic | `/scan` | |
| Map topic | `/map` | |
| Odometry topic | `/odom` | Change to `/odometry/filtered` when EKF running |
| IMU topic | `/imu/data` | |

Settings persist in `localStorage` and merge with defaults on page load.

### Launch file parameters

```bash
ros2 launch orbibot_webgui webgui.launch.py \
    rosbridge_port:=9090 \
    use_video:=true \
    webrtc_port:=8081
```

### Config file

`config/webgui_params.yaml` documents the available parameters and their defaults.
The launch file currently hard-codes these values; pass them as arguments to override.

---

## ROS 2 Interface

### Subscribed topics (frontend via rosbridge)

| Topic | Type | Used for |
|-------|------|---------|
| `/odom` | `nav_msgs/Odometry` | Raw odometry, path trace |
| `/odometry/filtered` | `nav_msgs/Odometry` | Filtered path trace, comparison charts |
| `/scan` | `sensor_msgs/LaserScan` | LiDAR view + diagnostics stats |
| `/imu/data` | `sensor_msgs/Imu` | IMU widget, attitude indicator |
| `/imu/data_raw` | `sensor_msgs/Imu` | Gyro/accel time-series (diagnostics) |
| `/imu/mag` | `sensor_msgs/MagneticField` | Magnetometer scatter plot |
| `/joint_states` | `sensor_msgs/JointState` | Per-wheel velocity + position |
| `/map` | `nav_msgs/OccupancyGrid` | SLAM map |
| `/orbibot/system_status` | `orbibot_msgs/SystemStatus` | Battery, motor status |
| `/orbibot/system_status_enriched` | `orbibot_msgs/SystemStatus` | CPU, RAM, temp, disk |
| `/orbibot/safety_status` | `orbibot_msgs/SafetyStatus` | E-stop, fault flags |
| `/orbibot/encoders` | `orbibot_msgs/EncoderStamped` | Encoder counts |
| `/plan` | `nav_msgs/Path` | Planned path overlay |
| `/navigate_to_pose/_action/status` | `action_msgs/GoalStatusArray` | Goal tracking |
| `/orbibot/emergency_stop` | `std_msgs/Bool` | E-stop monitor |
| `/orbibot/exploration/frontiers` | `visualization_msgs/MarkerArray` | Frontier count |
| `/orbibot/exploration/status` | `std_msgs/String` | Exploration state |
| `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | System diagnostics |

### Published topics (frontend via rosbridge)

| Topic | Type | Used for |
|-------|------|---------|
| `/cmd_vel` | `geometry_msgs/Twist` | Velocity commands |
| `/goal_pose` | `geometry_msgs/PoseStamped` | Navigation goals |
| `/initialpose` | `geometry_msgs/PoseWithCovarianceStamped` | Init pose |
| `/orbibot/pid_params` | `std_msgs/Float32MultiArray` | Motor PID `[kp, ki, kd]` |
| `/orbibot/pid_save` | `std_msgs/Float32MultiArray` | Save motor PID to flash |
| `/orbibot/yaw_pid_params` | `std_msgs/Float32MultiArray` | Yaw PID `[kp, ki, kd]` |
| `/orbibot/yaw_pid_save` | `std_msgs/Float32MultiArray` | Save yaw PID to flash |
| `/orbibot/beep` | `std_msgs/UInt16` | Buzzer test (duration ms) |
| `/orbibot/exploration/command` | `std_msgs/String` | `start` / `pause` / `stop` |

### Services called

| Service | Type | Used for |
|---------|------|---------|
| `/orbibot/get_firmware_version` | `orbibot_msgs/GetFirmwareVersion` | Display firmware version |
| `/orbibot/set_motor_enable` | `orbibot_msgs/SetMotorEnable` | Motor enable/disable toggle |
| `/orbibot/calibrate_imu` | `orbibot_msgs/CalibrateIMU` | Magnetometer calibration |
| `/orbibot/reset_encoders` | `orbibot_msgs/ResetEncoders` | Zero encoder counts |
| `/orbibot/reset_odometry` | `orbibot_msgs/ResetOdometry` | Zero odometry pose |
| `/navigate_to_pose/_action/cancel_goal` | `action_msgs/CancelGoal` | Cancel navigation |
| `/map_saver/save_map` | `nav2_msgs/SaveMap` | Save SLAM map |

### WebRTC server topic

| Topic | Type | Direction |
|-------|------|----------|
| `/camera/color/image_raw` | `sensor_msgs/Image` | Subscribed by Python node |

---

## Project Structure

```
orbibot_webgui/
├── orbibot_webgui/
│   └── webrtc_server.py        # ROS 2 node: camera → WebRTC stream
├── launch/
│   └── webgui.launch.py        # Starts rosbridge + WebRTC server
├── config/
│   └── webgui_params.yaml      # Port and topic defaults
├── scripts/
│   └── demo-robot.js           # Mock ROS data publisher for local dev
├── webgui-changelog.md
├── webgui-issue.md
└── frontend/src/
    ├── main.tsx                 # Entry point
    ├── App.tsx                  # Provider stack
    ├── lib/
    │   ├── constants.ts         # Topics, message types, robot params, UI defaults
    │   ├── math.ts              # quaternionToEuler, quaternionToYaw
    │   ├── logger.ts            # Dev-only logger (silent in production)
    │   ├── utils.ts             # cn() class-name helper
    │   └── webrtc/              # WebRTC signaling helpers
    ├── contexts/
    │   ├── SettingsContext.tsx  # App-wide config, persisted to localStorage
    │   ├── RosContext.tsx       # rosbridge connection + reconnect
    │   ├── WebRTCContext.tsx    # WebRTC stream lifecycle
    │   ├── NavigationContext.tsx # Waypoints, nav status, path, mode
    │   └── PathContext.tsx      # Client-side routing (dashboard / diagnostics)
    ├── hooks/
    │   ├── useSubscriber.ts     # Generic ROS topic subscriber
    │   ├── usePublisher.ts      # Generic ROS topic publisher
    │   ├── useCmdVel.ts         # Velocity command publisher
    │   ├── useBattery.ts        # Battery status
    │   ├── useEncoders.ts       # Encoder counts
    │   ├── useIMU.ts            # IMU data (orientation, angular velocity)
    │   ├── useRawIMU.ts         # Raw IMU (gyro + accel)
    │   ├── useMagnetometer.ts   # Magnetometer field
    │   ├── useJointStates.ts    # Per-wheel velocity + position from /joint_states
    │   ├── useCmdVelMonitor.ts  # Read-only /cmd_vel subscriber
    │   ├── useLidarScan.ts      # LaserScan data
    │   ├── useMap.ts            # OccupancyGrid data
    │   ├── useOdometry.ts       # Odometry data
    │   ├── useOdometryPath.ts   # Accumulated XY path (raw + filtered, ring buffer)
    │   ├── useTimeSeriesBuffer.ts # Single-channel time-series ring buffer
    │   ├── useMultiChannelTimeSeries.ts # N-channel time-series ring buffer
    │   ├── useSystemStatus.ts   # System/enriched status
    │   ├── useSafetyStatus.ts   # Safety status
    │   ├── useMotorControl.ts   # Motor enable + PID
    │   ├── useDataRecorder.ts   # Record topics to memory, export CSV
    │   ├── useWebRTC.ts         # WebRTC peer connection
    │   ├── useChat.ts           # AI chat (SSE streaming, provider, cancel)
    │   └── ...                  # Navigation, patrol, keyboard, touch hooks
    ├── components/
    │   ├── layout/              # Dashboard, Header, MissionControl, UnifiedViewport
    │   ├── common/              # ConnectionStatusBar, SettingsPanel, ErrorBoundary, etc.
    │   ├── navigation/          # NavigationToolbar, WaypointManager, ExplorationPanel, ChatPanel
    │   └── visualization/       # MapView, LidarView
    ├── features/
    │   ├── control/             # MecanumController, DirectionButton, VirtualJoystick
    │   ├── telemetry/           # Battery, Encoders, IMU, Odometry, PIDTuningPanel, etc.
    │   ├── diagnostics/         # Diagnostics page panels + charts
    │   │   ├── charts/          # TimeSeriesChart, ScatterPlot (reusable D3 components)
    │   │   ├── BatteryChart.tsx
    │   │   ├── ConnectionHealthPanel.tsx
    │   │   ├── DataExportPanel.tsx
    │   │   ├── DiagnosticsSection.tsx
    │   │   ├── FirmwareInfoPanel.tsx
    │   │   ├── IMUDetailPanel.tsx
    │   │   ├── LidarDiagnosticsPanel.tsx
    │   │   ├── MagnetometerPanel.tsx
    │   │   ├── MotorDetailPanel.tsx
    │   │   ├── OdometryComparisonChart.tsx
    │   │   ├── OdometryPathTrace.tsx
    │   │   └── WheelCalibrationWizard.tsx
    │   └── video/               # CameraFeed
    ├── pages/
    │   └── DiagnosticsPage.tsx  # 6-tab diagnostics workbench
    └── types/
        ├── ros.ts               # TypeScript interfaces for ROS message types
        └── interaction.ts       # InteractionMode, Waypoint, GoalStatus, etc.
```

---

## Developer Guide

### Adding a new ROS topic (read)

1. Add the topic name to `lib/constants.ts` → `ROS_TOPICS`.
2. Add the message type string to `ROS_MESSAGE_TYPES`.
3. Add a TypeScript interface to `types/ros.ts`.
4. Create a hook in `hooks/` that calls `useSubscriber<T>({ topic, messageType })`.
5. Use the hook in a component or feature.

Example — subscribing to `/orbibot/wheel_temp`:
```typescript
// lib/constants.ts
export const ROS_TOPICS = {
  ...
  wheelTemp: '/orbibot/wheel_temp',
} as const;

// hooks/useWheelTemp.ts
import { useSubscriber } from './useSubscriber';
import { ROS_TOPICS, ROS_MESSAGE_TYPES } from '@/lib/constants';

export function useWheelTemp() {
  const { data } = useSubscriber<Float32MultiArray>({
    topic: ROS_TOPICS.wheelTemp,
    messageType: ROS_MESSAGE_TYPES.float32MultiArray,
  });
  return data;
}
```

### Adding a new publisher

Use `usePublisher` from `hooks/usePublisher.ts`:

```typescript
const pub = usePublisher({ topic: '/my/topic', messageType: 'std_msgs/String' });
pub.publish({ data: 'hello' });
```

### Adding a new diagnostics panel

1. Create a component in `features/diagnostics/`.
2. For time-series data, use `TimeSeriesChart` from `features/diagnostics/charts/`.
3. For 2D scatter/path plots, use `ScatterPlot` from `features/diagnostics/charts/`.
4. Wrap with `DiagnosticsSection` for consistent heading + border.
5. Import and place in `DiagnosticsPage.tsx` under the appropriate tab.

### Adding a new UI panel

1. Create a component in `features/` or `components/`.
2. Import and place it in `Dashboard.tsx`, `MissionControl.tsx`, or `DiagnosticsPage.tsx`.
3. If it needs ROS data, use the appropriate hook.

### Adding a new page/route

1. Add the route path to `PathContext.tsx`.
2. Create a page component in `pages/`.
3. Render it in `App.tsx` based on the current path.

### Configuring a new setting

1. Add the field to `AppSettings` in `SettingsContext.tsx`.
2. Add a default value to `DEFAULT_SETTINGS`.
3. Add an input to `SettingsPanel.tsx`.
4. Read `settings.yourField` wherever needed.

---

## Keyboard Shortcuts

Press `?` at any time to open the shortcuts dialog.

| Category | Key | Action |
|----------|-----|--------|
| Control | W / ↑ | Forward |
| | S / ↓ | Backward |
| | A / ← | Strafe left |
| | D / → | Strafe right |
| | Q | Rotate CCW |
| | E | Rotate CW |
| | Space / Esc | Emergency stop |
| | 1–9 | Speed 10–90% |
| Navigation | I | Init pose mode |
| | G | Navigation goal mode |
| | Shift+W | Waypoint placement mode |
| Exploration | X | Start/resume exploration |
| | P | Pause exploration |
| | Ctrl+S | Save map |
| General | ? | Show shortcuts dialog |
| | Ctrl+T | Toggle dark/light theme |

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| "Failed to connect to rosbridge" | rosbridge not running | `ros2 launch orbibot_webgui webgui.launch.py` |
| Camera shows "unavailable" | WebRTC server not running | Launch with `use_video:=true`; check port 8081 |
| "No data" on telemetry panels | Topics not publishing | `ros2 topic hz /scan` — check robot stack is running |
| Navigation goals do nothing | Nav2 not running | `ros2 launch orbibot_navigation navigation.launch.py` |
| AI chat "offline" | chat_server not running | `ros2 launch orbibot_agent chat_server.launch.py` |
| WebRTC video black/frozen | Camera topic not publishing | `ros2 topic hz /camera/color/image_raw` |
| High video latency | Network congestion or WiFi | Use wired Ethernet; reduce camera resolution |
| Can't reach GUI from phone | Wrong IP in settings | Change WebSocket URL to `ws://robot_ip:9090` |
| `cv_bridge not available` | Package missing | `sudo apt install ros-jazzy-cv-bridge` |
| Diagnostics charts show "No data" | Topics not publishing or wrong topic name | Run `node scripts/demo-robot.js` to test with mock data |
| Joint states tab empty | `/joint_states` not publishing | Ensure robot hardware node is running at 50 Hz |

---

## Changelog

See [webgui-changelog.md](./webgui-changelog.md).

## Known Issues

See [webgui-issue.md](./webgui-issue.md).

---

## References

- [rosbridge_suite](https://github.com/RobotWebTools/rosbridge_suite)
- [roslib (JavaScript)](https://github.com/RobotWebTools/roslibjs)
- [aiortc](https://github.com/aiortc/aiortc)
- [Nav2](https://docs.nav2.org/)
- [shadcn/ui](https://ui.shadcn.com/)
- [D3.js](https://d3js.org/)
- [sonner](https://sonner.emilkowal.ski/)

---

**Maintainer:** Jewel Nath \<jewel.nath@orbitax.com\>
**Last updated:** 2026-03-27
