---
title: "orbibot_teleop"
type: package
tags:
  - package
  - teleop
---

# orbibot_teleop

Gamepad teleop over `/joy`. **Dormant — do not wire it up.**

> **The API reference is `src/orbibot_teleop/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Status

Teleop is **web dashboard only**: a controller plugged into the operator's
laptop, read by the browser's Gamepad API, sent over rosbridge.

This package stays in the tree as a **network-independent fallback** — if the
wifi path ever proves unreliable, a gamepad on the Pi does not depend on it.

Until then:

- Do **not** `apt install ros-jazzy-joy`
- Do **not** start `controller.launch.py`
- Its `package.xml` has `<exec_depend>joy</exec_depend>`, so `rosdep install`
  will pull `joy` in. That is expected; it does not mean the package is in use.

It publishes `/cmd_vel` directly, so if it is ever revived it needs its own
topic first — [[command-pipeline]] reserves `/cmd_vel_joy` at priority 220.

## Related

[[packages-moc]] · [[command-pipeline]] · [[orbibot_webgui]]
