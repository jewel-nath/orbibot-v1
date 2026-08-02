---
title: "orbibot_exploration"
type: package
tags:
  - package
  - exploration
---

# orbibot_exploration

BFS frontier detection, driving Nav2. Custom — not `explore_lite`.

> **The API reference is `src/orbibot_exploration/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

| Interface | |
|---|---|
| `/orbibot/exploration/command` | `start` · `stop` · `pause` · `resume` |
| `/orbibot/exploration/status` | Current state |
| `/orbibot/exploration/frontiers` | Detected frontiers, for visualisation |

```bash
ros2 launch orbibot_bringup exploration.launch.py   # needs SLAM + Nav2
```

Uses `action_msgs/GoalStatus` constants rather than magic numbers.

## Open

Untested against a tuned Nav2 — it cannot be meaningfully evaluated until
Phase 6's gate is met. Termination when no reachable frontier remains is the
part most likely to be wrong.

## Related

[[packages-moc]] · [[orbibot_navigation]] · [[orbibot_slam]] · [[roadmap]]
