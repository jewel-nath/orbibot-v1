# OrbiBot WebGUI Frontend

React-based web dashboard for real-time robot monitoring, control, and autonomous navigation.

## Tech Stack

- **React 19** + **TypeScript 5.9** + **Vite 7**
- **TailwindCSS 4** + **Radix UI** primitives
- **roslib** - ROS 2 WebSocket communication via rosbridge
- **D3.js** - LiDAR scan and map visualization
- **sonner** - Toast notifications
- **next-themes** - Dark/light mode theming
- **Lucide React** - Icon library
- **react-resizable-panels** - Resizable dashboard layout

## Setup

```bash
npm install
npm run dev
```

Open **http://localhost:5173** in a browser.

Requires rosbridge running on `ws://localhost:9090` (configurable in Settings).

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start Vite dev server with HMR |
| `npm run build` | TypeScript check + production build |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint |
| `npm run lint:fix` | Run ESLint with auto-fix |
| `npm run format` | Format code with Prettier |
| `npm run format:check` | Check formatting without writing |

## Architecture

### Provider Stack (App.tsx)

```
ThemeProvider
  └── RosProvider (rosbridge WebSocket)
        └── WebRTCProvider (video streaming)
              └── NavigationProvider (nav state, waypoints, path)
                    └── Dashboard UI
```

### Contexts

| Context | File | Purpose |
|---------|------|---------|
| **RosContext** | `contexts/RosContext.tsx` | rosbridge WebSocket connection, auto-reconnect |
| **WebRTCContext** | `contexts/WebRTCContext.tsx` | WebRTC peer connection for low-latency video |
| **NavigationContext** | `contexts/NavigationContext.tsx` | Interaction modes, waypoints, path, goal status |

### Components

#### Layout
| Component | Description |
|-----------|-------------|
| `Header` | Top navbar with connection status, theme toggle, settings |
| `Dashboard` | Responsive grid layout container |

#### Common
| Component | Description |
|-----------|-------------|
| `ConnectionStatus` | ROS connection state badge |
| `ErrorBoundary` | Error catching wrapper |
| `SettingsPanel` | Configuration modal (URLs, topics, speed limits) |
| `Skeleton` | Loading placeholder |
| `ThemeToggle` | Dark/light mode switcher |

#### Control
| Component | Description |
|-----------|-------------|
| `MecanumController` | Virtual joystick for omnidirectional drive |
| `DirectionButton` | Discrete directional movement button |
| `EmergencyStop` | E-stop button that zeroes `/cmd_vel` |

#### Telemetry
| Component | Description |
|-----------|-------------|
| `BatteryGauge` | Voltage display with full/low/critical color zones |
| `IMUWidget` | Roll, pitch, yaw with angular velocity graphs |
| `MotorStatus` | Per-motor speed and current display |
| `OdometryDisplay` | Position (x, y) and velocity readout |

#### Visualization
| Component | Description |
|-----------|-------------|
| `CameraFeed` | MJPEG or WebRTC video stream with fullscreen |
| `LidarView` | 2D LiDAR scan plot with zoom/pan controls |
| `MapView` | SLAM map with click-to-interact (pose, goal, waypoint, path overlay) |

#### Navigation
| Component | Description |
|-----------|-------------|
| `NavigationToolbar` | Mode selector (Init Pose, Nav Goal, Waypoint) with keyboard shortcuts |
| `WaypointManager` | Waypoint CRUD, drag reorder, patrol controls, import/export |
| `ExplorationPanel` | Frontier exploration start/pause/stop + map save |

#### Safety
| Component | Description |
|-----------|-------------|
| `ObstacleIndicator` | Obstacle detection status (clear/warning/emergency) with distance |

#### Video
| Component | Description |
|-----------|-------------|
| `WebRTCVideo` | WebRTC video player element |

### Hooks

#### Generic
| Hook | Description |
|------|-------------|
| `useSubscriber` | Generic ROS topic subscriber |
| `usePublisher` | Generic ROS topic publisher |
| `useWebRTC` | WebRTC connection management |

#### Sensor Subscriptions
| Hook | Topic | Description |
|------|-------|-------------|
| `useBattery` | `/orbibot/battery` | Battery voltage |
| `useEncoders` | `/orbibot/encoders` | Encoder counts |
| `useIMU` | `/imu/data` | IMU orientation and rates |
| `useLidarScan` | `/scan` | LiDAR scan ranges |
| `useMap` | `/map` | SLAM occupancy grid |
| `useMotors` | `/orbibot/motor_status` | Motor state |
| `useOdometry` | `/odom` | Position and velocity |

#### Navigation
| Hook | Topic | Description |
|------|-------|-------------|
| `useInitialPose` | `/initialpose` | Publish 2D Pose Estimate |
| `useNavGoal` | `/goal_pose` | Publish navigation goal + cancel |
| `usePath` | `/plan` | Subscribe to planned path with length calculation |
| `useWaypointPatrol` | - | Sequential waypoint navigation with loop/pause |

#### Control
| Hook | Topic | Description |
|------|-------|-------------|
| `useCmdVel` | `/cmd_vel` | Publish velocity commands |

### Types

| File | Contents |
|------|----------|
| `types/ros.ts` | ROS message type definitions |
| `types/interaction.ts` | `InteractionMode`, `Waypoint`, `MapClickEvent`, `GoalStatus` |
| `types/webrtc.ts` | `WebRTCConnectionState`, `WebRTCConfig` |

### Lib

| File | Contents |
|------|----------|
| `lib/constants.ts` | Global constants (default topics, limits) |
| `lib/utils.ts` | Utility functions (`cn` class merger, etc.) |
| `lib/webrtc-config.ts` | WebRTC configuration (STUN servers, etc.) |
| `lib/webrtc/signaling.ts` | WebRTC SDP signaling client |

## Source Structure

```
src/
├── main.tsx                        # Entry point
├── App.tsx                         # Root with provider stack
├── components/
│   ├── common/                     # ConnectionStatus, ErrorBoundary, Settings, Theme
│   ├── control/                    # MecanumController, DirectionButton, EmergencyStop
│   ├── layout/                     # Dashboard, Header
│   ├── navigation/                 # NavigationToolbar, WaypointManager, ExplorationPanel
│   ├── safety/                     # ObstacleIndicator
│   ├── telemetry/                  # BatteryGauge, IMUWidget, MotorStatus, OdometryDisplay
│   ├── video/                      # WebRTCVideo
│   └── visualization/              # CameraFeed, LidarView, MapView
├── contexts/                       # RosContext, WebRTCContext, NavigationContext
├── hooks/                          # 15 custom hooks
├── lib/                            # Constants, utils, WebRTC signaling
├── types/                          # TypeScript definitions
├── assets/                         # Static assets
└── styles/                         # Global styles
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `I` | Toggle Init Pose mode |
| `G` | Toggle Nav Goal mode |
| `W` | Toggle Waypoint placement mode |
| `Esc` | Cancel current interaction mode |

## Configuration

All settings are configurable via the in-app Settings panel and persisted in `localStorage`:

- **ROSBridge URL**: WebSocket address (default `ws://localhost:9090`)
- **Video Mode**: MJPEG or WebRTC
- **Camera Server**: MJPEG server URL (default `http://localhost:8080`)
- **WebRTC Server**: WebRTC signaling URL (default `http://localhost:8081`)
- **Max Linear Velocity**: Speed cap in m/s
- **Max Angular Velocity**: Rotation cap in rad/s
- **ROS Topic Names**: Customizable topic paths

## License

MIT
