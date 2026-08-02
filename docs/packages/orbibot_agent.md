---
title: "orbibot_agent"
type: package
tags:
  - package
  - agent
---

# orbibot_agent

The AI layer. Multi-LLM (Gemini, Claude, Kimi, Ollama), 62 robot tools, three
interfaces: HTTP API, terminal CLI, and an MCP server.

> **The API reference is `src/orbibot_agent/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

```bash
ros2 launch orbibot_agent chat_server.launch.py
ros2 launch orbibot_agent mcp_server.launch.py
```

Config: `agent_params.yaml`, `system_prompt.txt`.

Talks to ROS 2 through a **native bridge**, not rosbridge — `core/ros_bridge/`.

## Open

- `agent-issues.md` — 3 entries
- `core/ros_bridge/motion.py` publishes `/cmd_vel` directly. Once the pipeline
  is arbitrated it must move to its own topic, at a priority *below* the
  dashboard's — a human must always be able to override the agent.
  [[command-pipeline]]

## History

Replaced `orbibot_ai` and `orbibot_mcp_server`, both deleted. Ignore any note
that still mentions them.

## Related

[[packages-moc]] · [[command-pipeline]] · [[orbibot_webgui]]
