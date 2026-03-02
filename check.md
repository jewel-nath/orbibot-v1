ros2 node list
/imu_filter_madgwick
/launch_ros_2512
/orbibot_hardware_node
/robot_localization_ekf
/robot_state_publisher
/rplidar_node
/slam_toolbox
/transform_listener_impl_aaaae0bf3e00
/transform_listener_impl_aaaae10b4910



orbitax@orbibot:~/orbibot_ws$ ros2 topic list
/cmd_vel
/diagnostics
/imu/data
/imu/data_filtered
/imu/data_raw
/imu/mag
/joint_states
/map
/map_metadata
/odom
/odometry/filtered
/orbibot/beep
/orbibot/encoders
/orbibot/pid_multilevel
/orbibot/pid_params
/orbibot/pid_save
/orbibot/safety_status
/orbibot/system_status
/orbibot/system_status_enriched
/orbibot/yaw_pid_params
/parameter_events
/pose
/robot_description
/rosout
/scan
/set_pose
/slam_toolbox/feedback
/slam_toolbox/graph_visualization
/slam_toolbox/scan_visualization
/slam_toolbox/transition_event
/slam_toolbox/update
/tf
/tf_static


ros2 launch orbibot_bringup robot.launch.py 
[INFO] [launch]: All log files can be found below /home/orbitax/.ros/log/2026-03-02-22-17-12-829693-orbibot-2059
[INFO] [launch]: Default logging verbosity is set to INFO
[INFO] [launch.user]: [Bringup] Robot base started — camera: false
[INFO] [launch.user]: [Hardware] Starting hardware interface — port: /dev/motordriver
[INFO] [robot_state_publisher-1]: process started with pid [2063]
[INFO] [hardware_node-2]: process started with pid [2064]
[INFO] [system_monitor-3]: process started with pid [2065]
[robot_state_publisher-1] [INFO] [1772468233.629972795] [robot_state_publisher]: Robot initialized
[system_monitor-3] [INFO] [1772468234.139536543] [system_monitor]: System Monitor Node started - enriching /system_status
[hardware_node-2] [INFO] [1772468234.340899336] [orbibot_hardware_node]: Parameters validated: max_vel=1.0 m/s, sensor_rate=50 Hz
[hardware_node-2] [INFO] [1772468234.410882348] [orbibot_hardware_node]: Connecting to ROSMaster on /dev/motordriver...
[hardware_node-2] [INFO] [1772468234.688854936] [orbibot_hardware_node]: ROSMaster connected successfully
[hardware_node-2] [INFO] [1772468234.689703620] [orbibot_hardware_node]: OrbiBot Hardware Node started (Yahboom-compatible)
[INFO] [launch.user]: [Localization] Madgwick + EKF — /imu/data_raw + /imu/mag → absolute yaw → /odometry/filtered
[INFO] [motor_enable_startup-4]: process started with pid [2113]
[INFO] [imu_filter_madgwick_node-5]: process started with pid [2114]
[INFO] [ekf_node-6]: process started with pid [2115]
[imu_filter_madgwick_node-5] [INFO] [1772468236.279352135] [imu_filter_madgwick]: Starting ImuFilter
[imu_filter_madgwick_node-5] [INFO] [1772468236.279715967] [imu_filter_madgwick]: Using dt computed from message headers
[imu_filter_madgwick_node-5] [INFO] [1772468236.279735634] [imu_filter_madgwick]: The gravity vector is kept in the IMU message.
[imu_filter_madgwick_node-5] [INFO] [1772468236.279833819] [imu_filter_madgwick]: Imu filter gain set to 0.100000
[imu_filter_madgwick_node-5] [INFO] [1772468236.279851819] [imu_filter_madgwick]: Gyro drift bias set to 0.000000
[imu_filter_madgwick_node-5] [INFO] [1772468236.279862689] [imu_filter_madgwick]: Magnetometer bias values: 0.000000 0.000000 0.000000
[imu_filter_madgwick_node-5] [INFO] [1772468237.951708303] [imu_filter_madgwick]: First pair of IMU and magnetometer messages received.
[hardware_node-2] [INFO] [1772468237.969218584] [orbibot_hardware_node]: Motors enabled
[INFO] [launch.user]: [Bringup] Starting LiDAR as subprocess...
[INFO] [lidar_launch-7]: process started with pid [2159]
[INFO] [motor_enable_startup-4]: process has finished cleanly [pid 2113]
[lidar_launch-7] [INFO] [launch]: All log files can be found below /home/orbitax/.ros/log/2026-03-02-22-17-18-623837-orbibot-2159
[lidar_launch-7] [INFO] [launch]: Default logging verbosity is set to INFO
[lidar_launch-7] [INFO] [launch.user]: [Sensors] Starting RPLIDAR A1 — mode: Express, port: /dev/lidar
[lidar_launch-7] [INFO] [rplidar_composition-1]: process started with pid [2162]
[lidar_launch-7] [rplidar_composition-1] [INFO] [1772468238.794005662] [rplidar_node]: RPLidar running on ROS2 package rplidar_ros. RPLIDAR SDK Version:2.1.0
[lidar_launch-7] [rplidar_composition-1] [INFO] [1772468238.818114449] [rplidar_node]: RPLidar S/N: A3C6ED95C4E493CBA5E69EF032164B6F
[lidar_launch-7] [rplidar_composition-1] [INFO] [1772468238.818178541] [rplidar_node]: Firmware Ver: 1.29
[lidar_launch-7] [rplidar_composition-1] [INFO] [1772468238.818197356] [rplidar_node]: Hardware Rev: 7
[lidar_launch-7] [rplidar_composition-1] [INFO] [1772468238.819585687] [rplidar_node]: RPLidar health status : 0
[lidar_launch-7] [rplidar_composition-1] [INFO] [1772468238.819626038] [rplidar_node]: RPLidar health status : OK.
[lidar_launch-7] [rplidar_composition-1] [INFO] [1772468238.822691347] [rplidar_node]: Start
[lidar_launch-7] [rplidar_composition-1] [INFO] [1772468239.009139095] [rplidar_node]: current scan mode: Express, sample rate: 4 Khz, max_distance: 12.0 m, scan frequency:10.0 Hz, 
[ekf_node-6] [ERROR] [1772468630.240359537] [robot_localization_ekf]: Failed to meet update rate! Took 0.058607855999999999841seconds. Try decreasing the rate, limiting sensor output frequency, or limiting the number of sensors.



ros2 launch orbibot_slam slam.launch.py 
[INFO] [launch]: All log files can be found below /home/orbitax/.ros/log/2026-03-02-22-19-06-341992-orbibot-2512
[INFO] [launch]: Default logging verbosity is set to INFO
/opt/ros/jazzy/lib/python3.12/site-packages/launch_ros/events/lifecycle/lifecycle_node_matchers.py:30: UserWarning: 'matches_node_name' has been moved into the 'launch.events' module and will be removed from the 'lifecycle' module in the future
  warnings.warn(
[INFO] [launch.user]: [SLAM] Mapping mode started — scan: /scan, frames: odom → base_footprint → lidar_link
       params: /home/orbitax/orbibot_ws/install/orbibot_slam/share/orbibot_slam/config/slam_params.yaml
[INFO] [async_slam_toolbox_node-1]: process started with pid [2528]
[async_slam_toolbox_node-1] [INFO] [1772468346.893288732] [slam_toolbox]: Node using stack size 40000000
[async_slam_toolbox_node-1] [INFO] [1772468347.196631287] [slam_toolbox]: Configuring
[async_slam_toolbox_node-1] [INFO] [1772468347.276091647] [slam_toolbox]: Using solver plugin solver_plugins::CeresSolver
[async_slam_toolbox_node-1] [INFO] [1772468347.276354660] [slam_toolbox]: CeresSolver: Using SCHUR_JACOBI preconditioner.
[INFO] [launch.user]: [SLAM] Configured, activating...
[async_slam_toolbox_node-1] [INFO] [1772468347.329902518] [slam_toolbox]: Activating
[async_slam_toolbox_node-1] [INFO] [1772468347.693920913] [slam_toolbox]: Message Filter dropping message: frame 'lidar_link' at time 1772468347.448 for reason 'discarding message because the queue is full'
[async_slam_toolbox_node-1] Registering sensor: [Custom Described Lidar]
[ERROR] [async_slam_toolbox_node-1]: process has died [pid 2528, exit code -9, cmd '/opt/ros/jazzy/lib/slam_toolbox/async_slam_toolbox_node --ros-args --log-level info --ros-args -r __node:=slam_toolbox -r __ns:=/ --params-file /home/orbitax/orbibot_ws/install/orbibot_slam/share/orbibot_slam/config/slam_params.yaml'].

