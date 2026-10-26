# OrbiBot Web GUI — Changelog

---

## [Unreleased]

### [REFACTOR] Extract shared quaternion-to-Euler utility
- Duplicated `quaternionToEuler` function removed from `useIMU.ts` and `useOdometry.ts`
- Single implementation now lives in `lib/math.ts`

### [FIX] Chat API URL is now configurable
- `CHAT_API_BASE` was hardcoded to `hostname:8082` in two separate files
- Added `chatApiUrl` field to `AppSettings` (default: `http://hostname:8082`)
- `useChat` reads the URL from settings; `ChatPanel` does the same for direct fetch calls
- URL is now exposed in the Settings panel under **Connection → Chat API Server**

### [REFACTOR] Nav goal status codes replaced with named constants
- Magic numbers `1, 2, 4, 5, 6` in `NavigationContext` replaced with `NAV_STATUS` object
  (`ACCEPTED`, `EXECUTING`, `SUCCEEDED`, `CANCELED`, `ABORTED`)
- Matches `action_msgs/GoalStatus` field values

### [CHORE] Remove G15 code review markers from RosContext
- Internal annotation comments (`G15: ...`) replaced with plain English comments

---

## [2.1.0] — 2026-02

### [IMPROVEMENT] AI Chat panel (orbibot_agent integration)
- SSE streaming support: live text chunks and tool-call badges
- RobotTester mode with pass/fail test suite and AI review
- Provider selector (Gemini, Claude, Kimi, Ollama)
- Quick-action and nav-action buttons
- Offline indicator with retry on reconnect
- Markdown rendering for AI responses (tables, code blocks, lists)

### [IMPROVEMENT] PID Response Graph (Diagnostics page)
- Set target Vx/Vy/Wz, send command, record `/odom` response for 8 s
- Target vs actual overlay on same chart per axis

### [IMPROVEMENT] Diagnostics page
- Dedicated full-page view at `/diagnostics` (client-side routing)
- Sections: Robot Status, PID Tuning, PID Response Graph, Magnetometer Calibration

### [FIX] Navigation goal placement with rotated map
- `canvasToMap()` now applies the correct inverse rotation matrix
- Goals placed on a rotated map are sent to the correct world-frame coordinates

### [IMPROVEMENT] Waypoint patrol
- Drag-and-drop reorder, rename, import/export JSON
- Loop toggle and pause/resume for sequential patrol routes
- Persisted to `localStorage`

### [IMPROVEMENT] Frontier exploration panel
- Start / Pause / Stop buttons sending `std_msgs/String` to `/orbibot/exploration/command`
- Live frontier count from `/orbibot/exploration/frontiers`
- Map-save button via `nav2_map_server`

### [IMPROVEMENT] PID Tuning
- Single-motor and yaw PID sliders (0–10 range with validation)
- Apply sends to `/orbibot/pid_params`; Flash saves to robot flash via `/orbibot/pid_save`

### [IMPROVEMENT] Keyboard shortcuts
- Full shortcut set: WASD + arrows for movement, Q/E rotation, 1–9 speed, Space/Esc stop
- Navigation shortcuts: I (init pose), G (nav goal), Shift+W (waypoint), Ctrl+S (save map)
- Press `?` to open the shortcuts dialog

### [IMPROVEMENT] Telemetry fallback
- If `system_monitor` node is not running, telemetry falls back to `/orbibot/system_status`
- Battery gauge uses voltage as primary metric with 4S LiFePO4 thresholds

### [IMPROVEMENT] Connection status bar
- Top-of-screen warning for ROS/network disconnection
- Auto-dismisses on reconnect with brief "Reconnected" confirmation

---

## [2.0.0] — 2025-12

### [IMPROVEMENT] Full rewrite to React 19 + TypeScript + Vite
- Previous jQuery/vanilla-JS prototype replaced
- TailwindCSS + shadcn/ui component library
- Context API state management (RosContext, NavigationContext, SettingsContext, WebRTCContext)
- roslib WebSocket bridge replaces polling-based approach

### [IMPROVEMENT] WebRTC camera streaming
- aiortc-based Python ROS 2 node (`webrtc_server`)
- Thread-safe `FrameBuffer` class; ~50–100 ms end-to-end latency
- Graceful fallback when camera is offline (503 retry with fixed interval)

### [IMPROVEMENT] Mecanum controller
- 11-button directional grid for omnidirectional movement
- Dual virtual joystick mode for touch screens
- Continuous velocity publishing at 20 Hz while button/key held

### [IMPROVEMENT] Settings panel
- All connection parameters and topic names configurable in-app
- Persisted to `localStorage` (merges with defaults on load)

### [IMPROVEMENT] SLAM map view
- Real-time occupancy grid rendering on canvas
- Robot pose overlay, pan/zoom, track-up mode, fit-to-canvas
- Navigation toolbar: Init Pose / Nav Goal / Waypoint placement modes
