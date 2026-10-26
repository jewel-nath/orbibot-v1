# orbibot_sensors: known issues

| ID | Severity | Issue |
|---|---|---|
| SENS-1 | Medium | `obstacle_detector` is written but not started by any launch file, and nothing subscribes to its `/orbibot/emergency_stop` topic. It is not a safety layer yet. |
| SENS-2 | Low | The RealSense D435 enumerated at USB 2 speed (480 Mbps) on V1, which limits depth and colour together. See [the hardware page](../../docs/hardware/README.md). |
| SENS-3 | Low | No `/scan` rate is set in `config/rplidar_params.yaml`; the A1 spins at its default speed (nominal 5.5 Hz). |
