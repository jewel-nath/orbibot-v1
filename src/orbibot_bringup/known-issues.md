# orbibot_bringup: known issues

| ID | Severity | Issue |
|---|---|---|
| BRINGUP-1 | Medium | `mapping.launch.py` defaults `nav_params_file` to `nav2_params.yaml`, the AMCL variant. `nav2_params_slam.yaml` was written for navigating during SLAM, and `exploration.launch.py` already uses it. Pass `nav_params_file:=` until the default changes. |
| BRINGUP-2 | Low | `robot.launch.py` always enables the motors, 6 s after start: it includes `hardware.launch.py`, whose `motors_enabled` defaults to `true`, and does not declare that argument itself. To bring the base up with the motors off, start `hardware.launch.py motors_enabled:=false` on its own. |
