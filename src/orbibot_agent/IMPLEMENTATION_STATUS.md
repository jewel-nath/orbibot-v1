# OrbiBot Agent — Implementation Status

## Completed (65 tools)

| Category | Count | Tools |
|----------|-------|-------|
| Motion | 4 | move_robot, stop_robot, set_motor_enable, reset_firmware_state |
| Sensors | 14 | get_battery, get_imu, get_imu_raw, get_magnetometer, get_encoder_counts, get_joint_states, get_odometry, get_robot_position, get_lidar_summary, get_safety_status, get_system_enriched, get_firmware_version, get_all_firmware_data, list_topics |
| System / ROS | 7 | get_system_status, list_services, ros2_service_call, ros2_list_actions, ros2_send_action_goal, ros2_cancel_action_goal, ros2_action_request_result, ros2_action_subscribe_status, ros2_list_active_goals, ros2_topic_publish |
| Firmware | 9 | set_motor_pid, save_motor_pid, set_yaw_pid, save_yaw_pid, set_beep, reset_odometry, reset_encoders, calibrate_imu, set_mag_calibration |
| Testing | 8 | run_pid_test, run_motor_test, run_imu_test, run_encoder_test, run_mag_test, run_battery_test, run_beep_test, run_full_hardware_test |
| SLAM | 3 | slam_save_map, slam_serialize_map, slam_get_map_info |
| Nav2 | 11 | set_initial_pose, amcl_reinitialize, navigate_to_pose, navigate_through_poses, follow_waypoints, nav_cancel, nav_clear_costmaps, nav_spin, nav_backup, nav_get_plan |
| Exploration | 6 | exploration_start, exploration_stop, exploration_pause, exploration_resume, get_exploration_status, get_exploration_frontiers |

## Interfaces

- **Chat Server** — HTTP API with blocking + SSE streaming endpoints
- **Chat CLI** — Rich terminal interface with provider switching
- **MCP Server** — stdio protocol for Claude Desktop / Cline / Cursor
- **Test Suite** — LLM-free hardware test runner via `/api/run_test_suite`

## LLM Providers

- Gemini (google-genai SDK) — streaming
- Anthropic/Claude — streaming
- Moonshot/Kimi (OpenAI-compatible) — streaming
- Ollama (OpenAI-compatible, local) — streaming

## Future Work

- [ ] Topic subscribe with duration/message limits
- [ ] Camera image capture and object detection
- [ ] Navigate to named locations (location database)
- [ ] Patrol routes from config file
