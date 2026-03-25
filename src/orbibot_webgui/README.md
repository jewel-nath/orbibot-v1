# OrbiBot Web GUI

Modern web-based dashboard for real-time monitoring, control, and autonomous navigation of the OrbiBot mecanum-wheeled mobile robot.

## Features

### Real-Time Monitoring
- **Left sidebar (Telemetry)** - Safety status, system health (BATT, CPU, RAM, disk, temp), motors ON/OFF, encoders (FL/BL/FR/BR), odometry (wheel or fused source), IMU (orientation + Wz °/s). Fallback to base system_status when system_monitor is not running.
- **LiDAR Visualization** - Live 2D scan data with pan/zoom controls
- **IMU Telemetry** - Orientation, angular velocity (Wz °/s), and linear acceleration (full mode)
- **Camera Feed** - Low-latency video streaming via WebRTC (~50-100ms latency)
- **Odometry Display** - Position, velocity, and source label (Wheel vs Fused)
- **SLAM Map View** - Real-time occupancy grid with robot pose overlay
- **Battery Gauge** - Voltage as primary metric with status colors
- **Motor Status** - Encoder feedback and Motors ON/OFF badge
- **System Monitor** - CPU, RAM, temperature, disk usage via enriched system status

### Robot Control
- **Mecanum Controller** - 11-button directional pad for omnidirectional movement (8 directions + 2 rotation + stop)
- **Virtual Joystick** - Touch-friendly dual joystick mode (movement + rotation)
- **Keyboard Teleop** - WASD/Arrow keys with speed adjustment (1-9 keys set 10-90%)
- **Emergency Stop** - Immediate velocity reset with prominent button
- **Speed Control** - Adjustable speed slider with real-time velocity readout
- **PID Tuning** - Single motor and yaw PID gain adjustment (sliders + Apply/Flash) with input validation (gains 0–10). Located on the **Diagnostics** page. "Flash" saves motor PID to robot flash only; there is no single "save all" for all settings.
- **Settings Panel** - Configurable connection parameters and control limits

### Diagnostics (dedicated page)
- **Navigation** - Header link "Diagnostics" opens a full-page view (Robot Status, PID Tuning, PID Response Graph, Calibration).
- **Robot Status** - Safety, system health, encoders, odometry, IMU in one section.
- **PID Response Graph** - Set target Vx/Vy/Wz, Send to command the robot, record response from `/odom`; two lines per chart (target vs actual). Auto-stops after 8 s. See [pid-test-checklist.md](pid-test-checklist.md) for a step-by-step checklist (সব ঠিক আছে কিনা + ভালো PID মান বের করা).
- **Magnetometer calibration** - "Calibrate magnetometer" calls `/orbibot/calibrate_imu` (hard iron only; robot must be running).

### Autonomous Navigation
- **Navigation Toolbar** - Floating toolbar for Init Pose, Nav Goal, and Waypoint placement modes
- **Waypoint Manager** - Create, edit, rename, reorder (drag-and-drop), and delete waypoints
- **Patrol Routes** - Sequential waypoint navigation with pause/resume and loop toggle
- **Waypoint Persistence** - Save/load to localStorage, export/import as JSON files
- **Path Visualization** - Display planned path from Nav2 `/plan` topic
- **Goal Status** - Real-time feedback (navigating, succeeded, failed, canceled)
- **Cancel Navigation** - Abort current goal at any time

### Frontier Exploration
- **Exploration Panel** - Start/Pause/Stop autonomous frontier exploration
- **Frontier Count** - Real-time count of unexplored frontiers
- **Map Saving** - Save SLAM maps via nav2_map_server
- **Integration** - Works with orbibot_exploration package

### AI Chat (orbibot_agent integration)
- **Chat Panel** - Tab in MissionControl right panel for natural language robot control
- **SSE Streaming** - Live text chunks and tool execution badges as the AI works
- **Provider Selector** - Switch between Gemini, Claude, Kimi, Ollama from the header
- **RobotTester Mode** - Toggle for systematic hardware testing with pass/fail reporting
- **Quick Actions** - One-tap buttons for battery, position, IMU, status queries
- **Nav Actions** - Forward/backward/strafe/spin buttons in tester mode
- **Hardware Test Suite** - Run LLM-free tests with pass/fail display and AI review
- **Connection Status** - Offline indicator with retry when chat server is unreachable
- **Markdown Rendering** - Tables, code blocks, lists in AI responses

### Safety
- **Emergency Stop Monitor** - Monitors `/orbibot/emergency_stop` topic (e.g. from hardware/battery)
- **Connection Status Bar** - Top-of-screen warnings for ROS/network disconnection with auto-dismiss on reconnect

### Keyboard Shortcuts

Press `?` to open the shortcuts dialog at any time.

| Category | Shortcut | Action |
|----------|----------|--------|
| **Control** | `W` / `Arrow Up` | Move forward |
| | `S` / `Arrow Down` | Move backward |
| | `A` / `Arrow Left` | Strafe left |
| | `D` / `Arrow Right` | Strafe right |
| | `Q` | Rotate CCW |
| | `E` | Rotate CW |
| | `Space` / `Esc` | Emergency stop |
| | `1-9` | Set speed 10-90% |
| **Navigation** | `I` | Initial pose mode |
| | `G` | Navigation goal mode |
| | `Shift+W` | Waypoint placement mode |
| | `Esc` | Cancel / exit mode |
| **Exploration** | `X` | Start/Resume exploration |
| | `P` | Pause exploration |
| | `Ctrl+S` | Save map |
| **General** | `?` | Show shortcuts dialog |
| | `Ctrl+T` | Toggle theme |

### Video Streaming
- **WebRTC** - Low latency (~50-100ms) via dedicated WebRTC server
- **Efficient Frame Handling** - Thread-safe frame buffer with minimal lock contention
- **Expandable View** - Click-to-toggle camera and LiDAR overlay sizes

## Architecture

### Frontend (`frontend/`)
- **Framework**: React 19 + TypeScript + Vite
- **UI Library**: TailwindCSS + shadcn/ui components
- **ROS Communication**: roslib via rosbridge_suite (WebSocket)
- **Video Streaming**: WebRTC (RTCPeerConnection) with optimized frame buffer
- **State Management**: React Context API (RosContext, WebRTCContext, NavigationContext, PathContext for Dashboard/Diagnostics routing)
- **Notifications**: sonner toast library
- **Theming**: next-themes with dark mode default
- **Logging**: Development-only logger (no console noise in production)

### Backend (`orbibot_webgui/`)
- **WebRTC Server**: ROS 2 Python node using aiortc
  - Thread-safe `FrameBuffer` class for efficient frame sharing
  - No global state (proper dependency injection)
  - Graceful error handling for missing dependencies
- **Signaling**: REST-based (HTTP POST /offer)
- **Camera Integration**: Subscribes to ROS 2 Image topics with QoS best-effort

### Data Flow
```
ROS 2 Robot <-> rosbridge_server (WebSocket :9090)  <-> React Frontend
            <-> WebRTC Server (HTTP :8081)           <-> WebRTC Stream
            <-> Nav2 (navigate_to_pose action)       <-> Navigation Goals
            <-> orbibot_exploration (frontier search) <-> Exploration Panel
```

## Prerequisites

### System Requirements
- **OS**: Ubuntu 22.04+ / Debian-based Linux
- **ROS 2**: Jazzy Jalisco (or compatible distro)
- **Node.js**: v18+ (with npm)
- **Python**: 3.10+

### ROS 2 Dependencies
```bash
sudo apt update
sudo apt install ros-jazzy-rosbridge-suite ros-jazzy-cv-bridge
```

For navigation features:
```bash
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup
```

### Python Dependencies (WebRTC server)
```bash
pip3 install aiortc aiohttp aiohttp-cors av opencv-python
```

## Installation

### 1. Build ROS 2 Package

```bash
cd ~/OrbiBot  # or your workspace root
colcon build --packages-select orbibot_webgui
source install/setup.bash
```

### 2. Install Frontend Dependencies

```bash
cd src/orbibot_webgui/frontend
npm install
```

## Usage

### Development Mode

#### Step 1: Start ROS 2 Services

Terminal 1 - Launch rosbridge + WebRTC server:
```bash
ros2 launch orbibot_webgui webgui.launch.py
```

Or without video streaming:
```bash
ros2 launch orbibot_webgui webgui.launch.py use_video:=false
```

#### Step 2: Start Robot System

```bash
ros2 launch orbibot_bringup system.launch.py
ros2 launch orbibot_sensors sensors.launch.py
```

For navigation:
```bash
ros2 launch orbibot_navigation navigation.launch.py
```

For frontier exploration:
```bash
ros2 launch orbibot_exploration exploration.launch.py
```

#### Step 3: Run Frontend Development Server

```bash
cd src/orbibot_webgui/frontend
npm run dev
```

Open browser to: **http://localhost:5173** — Dashboard (map, telemetry, control) and **Diagnostics** (header link: Robot Status, PID Tuning, PID Response Graph, Calibration).

### Production Mode

#### Build Frontend

```bash
cd src/orbibot_webgui/frontend
npm run build
```

Built files will be in `frontend/dist/`.

#### Serve Production Build

Option 1 - Using Python HTTP server:
```bash
cd src/orbibot_webgui/frontend/dist
python3 -m http.server 5173
```

Option 2 - Using Nginx (recommended for robot deployment):
```bash
sudo apt install nginx
sudo cp -r src/orbibot_webgui/frontend/dist/* /var/www/html/
sudo systemctl restart nginx
```

### Configuration

#### Settings Panel (In-App)

Click the settings icon in the top-right corner to configure:

**Connection:**
- ROSBridge URL (default: `ws://localhost:9090`)
- WebRTC Server URL (default: `http://localhost:8081`)

**Control Limits:**
- Max Linear Velocity (m/s)
- Max Angular Velocity (rad/s)

**ROS Topics:**
- Scan, Map, Odometry, IMU topic names

Settings are persisted in browser localStorage.

#### Launch File Parameters

```bash
ros2 launch orbibot_webgui webgui.launch.py \
    rosbridge_port:=9090 \
    use_video:=true \
    webrtc_port:=8081
```

## ROS 2 Interface

### Subscribed Topics (Frontend reads via rosbridge)
| Topic | Type | Description |
|-------|------|-------------|
| `/odom` | `nav_msgs/Odometry` | Robot odometry (or `/odometry/filtered` when localization running) |
| `/scan` | `sensor_msgs/LaserScan` | LiDAR scan data |
| `/imu/data` | `sensor_msgs/Imu` | IMU sensor data |
| `/map` | `nav_msgs/OccupancyGrid` | SLAM map data |
| `/orbibot/system_status` | `orbibot_msgs/SystemStatus` | Battery, motor status |
| `/orbibot/system_status_enriched` | `orbibot_msgs/SystemStatus` | CPU, RAM, temp, disk metrics |
| `/orbibot/safety_status` | `orbibot_msgs/SafetyStatus` | E-stop, cmd timeout, low battery, faults |
| `/orbibot/encoders` | `std_msgs/Int32MultiArray` | Raw encoder counts |
| `/plan` | `nav_msgs/Path` | Planned navigation path |
| `/navigate_to_pose/_action/status` | `action_msgs/GoalStatusArray` | Navigation goal status |
| `/orbibot/emergency_stop` | `std_msgs/Bool` | Emergency stop status (e.g. hardware/battery) |
| `/orbibot/exploration/frontiers` | `visualization_msgs/MarkerArray` | Frontier markers |
| `/orbibot/exploration/status` | `std_msgs/String` | Exploration state |

### Subscribed Topics (WebRTC server)
| Topic | Type | Description |
|-------|------|-------------|
| `/camera/color/image_raw` | `sensor_msgs/Image` | Camera feed for WebRTC streaming |

### Published Topics (Frontend writes via rosbridge)
| Topic | Type | Description |
|-------|------|-------------|
| `/cmd_vel` | `geometry_msgs/Twist` | Velocity commands |
| `/goal_pose` | `geometry_msgs/PoseStamped` | Navigation goals |
| `/initialpose` | `geometry_msgs/PoseWithCovarianceStamped` | Initial pose estimate |
| `/orbibot/pid_params` | `std_msgs/Float32MultiArray` | Motor PID gains: `[kp, ki, kd]` (single PID for all motors) |
| `/orbibot/yaw_pid_params` | `std_msgs/Float32MultiArray` | Yaw PID gains: `[kp, ki, kd]` |
| `/orbibot/pid_save` | `std_msgs/Float32MultiArray` | Save motor PID to flash: `[kp, ki, kd]` (persists across power cycles; no "save all" for other settings) |
| `/orbibot/exploration/command` | `std_msgs/String` | Exploration commands (start/pause/stop) |

### Services Called
| Service | Type | Description |
|---------|------|-------------|
| `/orbibot/calibrate_imu` | `orbibot_msgs/CalibrateIMU` | Magnetometer (hard iron) calibration; used from Diagnostics → Calibration |
| `/navigate_to_pose/_action/cancel_goal` | `action_msgs/CancelGoal` | Cancel active navigation |
| `/map_saver/save_map` | `nav2_msgs/SaveMap` | Save current SLAM map |

## Project Structure

```
orbibot_webgui/
├── package.xml                         # ROS 2 package manifest
├── setup.py                            # Python package setup
├── setup.cfg                           # Install scripts config
├── README.md                           # This file
├── webgui-changelog.md                 # Detailed changelog
├── resource/
│   └── orbibot_webgui                  # ament index marker
├── orbibot_webgui/                     # Python backend
│   ├── __init__.py
│   └── webrtc_server.py                # WebRTC signaling + ROS 2 camera subscriber
├── launch/
│   └── webgui.launch.py                # Launches rosbridge + WebRTC server
├── config/
│   └── webgui_params.yaml              # Server ports, topics, control limits, rates
└── frontend/                           # React frontend application
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx                    # Entry point
        ├── App.tsx                     # Root component with provider stack
        ├── lib/
        │   ├── constants.ts            # Robot params, topics, UI config
        │   ├── utils.ts                # cn() class name helper
        │   ├── logger.ts               # Development-only logging
        │   ├── webrtc-config.ts
        │   └── webrtc/
        │       └── signaling.ts
        ├── contexts/                   # React Context providers
        │   ├── RosContext.tsx
        │   ├── WebRTCContext.tsx
        │   ├── NavigationContext.tsx
        │   ├── SettingsContext.tsx
        │   └── PathContext.tsx         # Dashboard vs Diagnostics routing
        ├── hooks/                      # Custom React hooks
        │   ├── useSubscriber.ts        # Generic ROS topic subscriber
        │   ├── usePublisher.ts         # Generic ROS topic publisher
        │   ├── useCmdVel.ts
        │   ├── useBattery.ts
        │   ├── useEncoders.ts
        │   ├── useIMU.ts
        │   ├── useLidarScan.ts
        │   ├── useMap.ts
        │   ├── useMotors.ts
        │   ├── useOdometry.ts
        │   ├── useOdomSampling.ts       # /odom sampling for PID Response Graph
        │   ├── useMotorControl.ts       # Motor enable service + PID hardware check
        │   ├── useSafetyStatus.ts
        │   ├── useInitialPose.ts
        │   ├── useNavGoal.ts
        │   ├── usePath.ts
        │   ├── useKeyboardShortcuts.ts
        │   ├── useNetworkStatus.ts
        │   ├── useWebRTC.ts
        │   ├── useTouchGestures.ts
        │   ├── useWaypointPatrol.ts
        │   └── useSystemStatus.ts
        ├── pages/
        │   └── DiagnosticsPage.tsx     # Full-page: Robot Status, PID Tuning, PID Graph, Calibration
        ├── features/
        │   ├── control/                # Robot control components
        │   ├── telemetry/              # PIDTuningPanel, PIDResponseGraph, ImuCalibrationSection, etc.
        │   └── video/                  # Camera feed
        ├── components/
        │   ├── layout/                 # Dashboard, Header, Viewport
        │   ├── common/                 # ConnectionStatus, ErrorBoundary, etc.
        │   ├── navigation/             # Nav2 integration
        │   ├── visualization/          # MapView, LidarView
        │   └── ui/                     # shadcn/ui primitives
        ├── types/                      # TypeScript type definitions
        └── styles/
            └── index.css
```

## Troubleshooting

### Frontend Issues

**Problem**: "Failed to connect to rosbridge"
- **Solution**: Check rosbridge_server is running on port 9090
  ```bash
  ros2 launch orbibot_webgui webgui.launch.py
  ```

**Problem**: Camera feed shows "Camera feed unavailable"
- **Solution**: Verify WebRTC server is running
  ```bash
  ros2 launch orbibot_webgui webgui.launch.py use_video:=true
  curl http://localhost:8081/  # Should return {"status": "ok"}
  ```

**Problem**: "No data received" on telemetry panels
- **Solution**: Check topics are publishing
  ```bash
  ros2 topic list
  ros2 topic hz /scan
  ros2 topic hz /imu/data
  ```

**Problem**: Navigation goals placed at wrong position when map is rotated
- **Solution**: Fixed — `canvasToMap()` now applies the correct inverse rotation matrix.

**Problem**: Navigation goal does nothing
- **Solution**: Ensure Nav2 stack is running
  ```bash
  ros2 launch orbibot_navigation navigation.launch.py
  ros2 topic echo /navigate_to_pose/_action/status
  ```

### Backend Issues

**Problem**: WebRTC server fails to start with "cv_bridge not available"
- **Solution**: Install cv_bridge
  ```bash
  sudo apt install ros-jazzy-cv-bridge
  ```

**Problem**: "No module named 'orbibot_webgui'"
- **Solution**: Rebuild and source the package
  ```bash
  colcon build --packages-select orbibot_webgui
  source install/setup.bash
  ```

**Problem**: WebRTC video is black/frozen
- **Solution**: Check camera topic is publishing
  ```bash
  ros2 topic hz /camera/color/image_raw
  ```

**Problem**: High video latency
- **Solution**:
  - Reduce resolution in launch file (640x480 -> 320x240)
  - Check network bandwidth
  - Use wired connection instead of WiFi

### Network Issues

**Problem**: Cannot access WebGUI from remote device
- **Solution**: Update WebSocket URL in Settings to robot's IP
  ```
  ws://192.168.x.x:9090  # Replace with robot IP
  ```

## Development

### Frontend Development

```bash
cd src/orbibot_webgui/frontend
npm run dev      # Start dev server
npm run lint     # Run linter
npm run build    # Production build
npm run format   # Format code
```

### Backend Development

Test WebRTC server standalone:
```bash
ros2 run orbibot_webgui webrtc_server \
    --ros-args \
    -p image_topic:=/camera/color/image_raw \
    -p port:=8081
```

### Mobile Controller

Access the full-screen touch controller for phone/tablet at:
```
http://robot_ip:5173/controller
```

## Changelog

See [webgui-changelog.md](./webgui-changelog.md) for detailed change history including:
- Performance optimizations
- Bug fixes
- Architecture improvements
- Testing checklist

## License

MIT

## References

- [rosbridge_suite](https://github.com/RobotWebTools/rosbridge_suite) - ROS WebSocket bridge
- [roslib](https://github.com/RobotWebTools/roslibjs) - JavaScript ROS client library
- [aiortc](https://github.com/aiortc/aiortc) - WebRTC Python implementation
- [Nav2](https://docs.nav2.org/) - ROS 2 Navigation stack
- [shadcn/ui](https://ui.shadcn.com/) - React component library
- [sonner](https://sonner.emilkowal.ski/) - Toast notification library