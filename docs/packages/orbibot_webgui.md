---
title: "orbibot_webgui"
type: package
tags:
  - package
  - webgui
---

# orbibot_webgui

The dashboard: rosbridge plus a WebRTC backend, and a React frontend.
**This is the only teleop path.**

> **The API reference is `src/orbibot_webgui/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

| | Port |
|---|---|
| rosbridge WebSocket | 9090 |
| WebRTC | 8081 |

```bash
ros2 launch orbibot_webgui webgui.launch.py
```

Frontend in `frontend/`. **`npm run build`, then serve `dist/`** — never run
the Vite dev server on the Pi.

## Why it matters more than it looks

Teleop is web-only, so **the network is the control path**. A dropped wifi link
is a runaway robot unless timeouts are real. That makes this package a safety
component, not a convenience — [[command-pipeline]].

## Open

- `webgui-issue.md` — 9 entries
- Publishes `/cmd_vel` directly, unarbitrated — [[backlog-moc]] CC-1
- Telemetry is ~15 separate rosbridge subscriptions; the design target is one
  aggregated 5–10 Hz message — [[dashboard-design]]

## Related

[[packages-moc]] · [[dashboard-design]] · [[command-pipeline]] ·
[[lgdxrobot2-chassistuner]]
