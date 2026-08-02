---
title: "Command Pipeline"
type: architecture
tags:
  - architecture
  - safety
  - cmd_vel
---

# Command Pipeline

How a velocity command should reach the wheels, and why the current path is
the most important thing to fix before driving the robot around a room.

---

## What exists today

Four independent publishers write to `/cmd_vel` with **no arbitration**:

| Publisher | Source |
|---|---|
| `orbibot_teleop` | `controller.py` — gamepad |
| `orbibot_webgui` | `useCmdVel.ts` / `usePublisher.ts` — browser |
| `orbibot_agent` | `core/ros_bridge.py` — LLM tool calls |
| Nav2 `collision_monitor` | `cmd_vel_out_topic: "cmd_vel"` |

Whoever publishes most recently wins. There is no priority, no way to
preempt, and no notion of a stale source. Concretely:

- Nav2 driving to a goal and a browser slider moving at the same time produces
  interleaved, contradictory commands at whatever rate each happens to publish
- Closing the dashboard tab mid-command leaves the last velocity applied until
  the **firmware's** 2 s timeout fires — the only backstop in the system
- The agent can issue a motion while a human is driving, with no indication to
  either side

Nav2's internal chain is correct and should stay:

```
controller_server → cmd_vel_nav → velocity_smoother → cmd_vel_smoothed
                                → collision_monitor → cmd_vel
```

The problem is only that `collision_monitor` shares its output topic with
three unrelated publishers.

## Target design

Insert `twist_mux` as the single writer of `/cmd_vel`. Every source publishes
to its own topic and is arbitrated by priority and timeout.

```
e-stop / zero        → /cmd_vel_estop     priority 255  timeout 0.5
web dashboard        → /cmd_vel_web       priority 200  timeout 0.3
AI agent             → /cmd_vel_agent     priority 100  timeout 1.0
Nav2 collision_mon.  → /cmd_vel_nav_out   priority  50  timeout 0.5
                                   ↓
                              twist_mux
                                   ↓
                             /cmd_vel  →  orbibot_hardware  →  firmware

(reserved, not wired: /cmd_vel_joy — Pi-side gamepad, priority 220)
```

Properties this buys:

- **Human always wins.** Driving from the dashboard overrides autonomous
  navigation without stopping Nav2 or unwinding any state.
- **Silence means stop.** A source that stops publishing is dropped after its
  timeout; the next-highest source takes over, and if none are live the mux
  publishes zero. Losing the browser tab stops the robot in 0.3 s instead of 2 s.
- **One writer.** `/cmd_vel` has exactly one publisher, so `ros2 topic info`
  becomes a real answer to "who is driving?"

### Teleop is web-only, so the network is the control path

The operator drives from the browser — a controller on their laptop read by the
Gamepad API, sent over rosbridge. There is no Pi-side gamepad in the loop.

That makes the web input's timeout the **shortest** in the system, and not
optional. A wifi drop, a closed laptop lid or a browser tab switch must all look
identical to the robot: commands stop arriving, so the robot stops. 0.3 s is
chosen to be shorter than a human notices but longer than normal jitter — tune
it against the measured round-trip, and never let it exceed the driver's
`cmd_timeout`.

`orbibot_teleop` (Pi-side `/joy`) stays in the tree as a network-independent
fallback but is **not wired up**. Its slot is reserved above so that adding it
later needs no renumbering.

`twist_mux` also publishes which input is active, which the dashboard should
display — the operator should never have to guess who has control.

## Layers of stop

Defence in depth, fastest first:

| Layer | Mechanism | Reaction |
|---|---|---|
| Firmware | `COMMAND_TIMEOUT_MS` 2000 | Last resort if serial dies |
| Firmware | Battery lockout below 10.5 V | Cuts motors |
| Driver | `cmd_timeout` in `hardware_params.yaml` | Stops if ROS goes quiet |
| Mux | Per-input timeout 0.5 s | Stops if a source goes quiet |
| Mux | E-stop topic at top priority | Immediate override |
| Nav2 | `collision_monitor` | Stops before a modelled collision |
| Hardware | PD2 user button — **unused today** | A real physical stop |

The firmware timeout is currently doing work that belongs at the mux layer.
Pushing detection earlier shortens the worst case from 2 s to 0.5 s.

## Why this comes before autonomy

Every later phase — mapping, navigation, exploration — adds another thing that
wants to drive the robot. Adding them on top of an unarbitrated topic means
each new capability makes the failure modes harder to reason about. Fixing the
pipeline once, early, keeps every later phase testable.

## Acceptance tests

1. Publish a constant velocity from the web source; start Nav2 driving a goal.
   The web source must win, and `twist_mux` must report it as active.
2. While the gamepad drives, publish from the agent. The gamepad must win.
3. Stop publishing from the active source. The robot must stop within its
   timeout — measured, not assumed.
4. Publish to the e-stop topic during any of the above. The robot must stop
   immediately and stay stopped while the e-stop keeps publishing.
5. `ros2 topic info /cmd_vel` must list exactly one publisher.

## Related

[[roadmap]] — Phase 2 implements this · [[orbibot_teleop]] ·
[[orbibot_webgui]] · [[orbibot_navigation]] · [[dashboard-design]]
