# OrbiBot Agent — Issues and Improvement Ideas

Remaining issues, technical debt, and improvement ideas after the 2026-03 refactor.

## Open Issues

### High Priority

- [ ] **No unit tests** — zero test coverage. Start with SafetyManager (pure logic), TestSuiteRunner, and provider initialization. Then add integration tests with a mock RosBridge.
- [ ] **Anthropic provider argument parsing inconsistency** — Anthropic SDK returns tool arguments as Python dicts; Moonshot/Ollama parse from JSON strings. Unify handling in all providers.

### Medium Priority

- [ ] **No vision tools** — camera image capture and object detection are planned. The `cv_bridge` dependency is already declared in `package.xml`.
- [ ] **Single concurrent session** — chat server uses a global lock; only one chat request processes at a time. Add session IDs for multi-user support.
- [ ] **No persistent conversation** — chat history resets on server restart. Consider persisting to disk or database.
- [ ] **Topic subscribe tool missing** — `ros2_topic_subscribe` with duration/message limits would let the LLM inspect arbitrary topics.

### Low Priority

- [ ] **Sensor read caching** — `wait_for_message` creates a subscription for every read. Add TTL-based caching for high-frequency topics (battery doesn't change in 1s).
- [ ] **Interface listing tool** — `ros2_interface_list` and `ros2_get_message_fields` for introspection.

## Improvement Ideas

| Area | Idea |
|------|------|
| **Testing** | Add `colcon test` with pytest fixtures mocking RosBridge |
| **ROS 2 patterns** | Use lifecycle node for chat_server (managed start/stop) |
| **Streaming** | Add WebSocket endpoint as alternative to SSE for bidirectional comms |
| **Observability** | Publish tool execution metrics to a ROS topic for dashboard monitoring |
| **Vision** | Add camera capture tool using cv_bridge — dependency already declared |
| **Navigation** | Navigate to named locations (requires location database) |
| **Navigation** | Patrol routes from config file |
| **Firmware** | Define shared Python dataclass for serial protocol frame (currently ad-hoc parsing in ros_bridge) |
| **Performance** | Cache sensor reads with TTL to reduce `wait_for_message` overhead |
| **Scalability** | Support multiple concurrent chat sessions with session IDs |

## Completed (2026-03 Refactor)

- [x] Extract `OpenAICompatProvider` base class (Moonshot + Ollama dedup)
- [x] Eliminate `AgentNode.__new__` hack in ChatServer and McpServer
- [x] Fix test_suite_runner tool name mismatches (get_battery, get_imu_raw, get_magnetometer)
- [x] Split `ros_bridge.py` (1906 lines) into 7 focused modules
- [x] Split `tool_registry.py` (1770 lines) into 7 focused modules
- [x] Add public API to AgentNode (properties instead of _private access)
- [x] Remove `web-chat-server-improvement.md` (obsolete planning doc)
- [x] Remove `IMPLEMENTATION_STATUS.md` (merged into README)
- [x] Clean up all Phase N comments and redundant docstrings
- [x] Fix chat_cli Rich import shadowing builtin
- [x] Update setup.py maintainer
