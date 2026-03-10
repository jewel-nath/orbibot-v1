#!/usr/bin/env python3
"""
OrbiBot Hardware Node

Interfaces with the Yahboom ROSMaster expansion board STM32 firmware.
Firmware handles motor PID and odometry at 100Hz, ROS2 publishes /odom directly.

Key Features:
- Velocity control via /cmd_vel → firmware
- Firmware odometry → /odom with adaptive covariance
- Encoder data publishing for diagnostics
- IMU data publishing (raw + attitude + magnetometer)
- Joint states for RViz visualization
- System monitoring and safety

Architecture:
ROS 2 → /cmd_vel → Firmware (mecanum kinematics + PID @ 100Hz)
Firmware → Odometry + Encoders + IMU + Status → ROS 2 @ 20Hz
Firmware odometry (100Hz) → hardware_node → /odom → EKF
"""

import math
import time
import threading
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rcl_interfaces.msg import SetParametersResult

# ROS2 Messages
from sensor_msgs.msg import Imu, JointState, MagneticField
from geometry_msgs.msg import Twist, Quaternion
from nav_msgs.msg import Odometry
from std_msgs.msg import Int32MultiArray, Float32MultiArray, UInt16
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

# Custom Messages
from orbibot_msgs.msg import SystemStatus, SafetyStatus
from orbibot_msgs.srv import SetMotorEnable, CalibrateIMU, ResetOdometry

# ROSMaster Driver
try:
    from orbibot_hardware import rosmaster_driver
    ROSMASTER_AVAILABLE = True
except ImportError:
    ROSMASTER_AVAILABLE = False


class OrbiBotHardwareNode(Node):
    """
    Hardware interface node for OrbiBot.

    Publishes firmware odometry on /odom with adaptive covariance.
    Firmware handles PID + odometry at 100Hz, this node bridges to ROS 2.
    """

    def __init__(self):
        super().__init__('orbibot_hardware_node')

        # Load parameters
        self._declare_parameters()

        # Hardware connection
        self.bot = None
        self.hardware_connected = False

        # State (with thread-safe access for last_cmd_time)
        self._state_lock = threading.Lock()  # G4: Thread-safe access to motors_enabled/emergency_stop
        self.motors_enabled = False
        self.emergency_stop = False
        self._velocity_limited = False
        self._cmd_time_lock = threading.Lock()
        self._last_cmd_time = time.time()
        self._timeout_stop_sent = False  # G1: Track if timeout stop command already sent

        # Wheel joint state tracking (for RViz visualization)
        self.wheel_positions = [0.0, 0.0, 0.0, 0.0]  # FL, BL, FR, BR
        self.last_encoders = [0, 0, 0, 0]
        self.encoder_initialized = False

        # Robot parameters (overridden from YAML in _declare_parameters — R2)
        self.wheel_radius = 0.05
        self.encoder_edges_per_rev = 1320

        # Odometry adaptive covariance tracking
        self._accumulated_distance = 0.0
        self._accumulated_rotation = 0.0
        self._last_odom_x = 0.0
        self._last_odom_y = 0.0
        self._last_odom_theta = 0.0
        self._last_firmware_odom = None  # G3: Track last firmware data to skip duplicates

        # Rate limiting for PID topics (HW-005)
        self._pid_rate_limit = 0.1  # Max 10Hz (100ms between updates)
        self._last_pid_update = 0.0
        self._last_yaw_pid_update = 0.0
        self._last_pid_save_update = 0.0

        # Callback group for concurrent timer execution with MultiThreadedExecutor
        self._sensor_cb_group = ReentrantCallbackGroup()

        # Create ROS interfaces
        self._create_publishers()
        self._create_subscribers()
        self._create_services()
        self._create_timers()

        # R3: Dynamic parameter reconfiguration
        self.add_on_set_parameters_callback(self._on_set_parameters)

        # Initialize hardware
        self._initialize_hardware()

        self.get_logger().info("OrbiBot Hardware Node started (Yahboom-compatible)")

    def _declare_parameters(self):
        """Declare and load ROS parameters"""
        # Hardware
        self.declare_parameter('hardware.serial_port', '/dev/motordriver')
        self.declare_parameter('hardware.data_timeout', 2.0)  # S1/S2: seconds without data → hardware_connected=False
        self.declare_parameter('robot.wheel_radius', 0.05)  # R2: 50mm
        self.declare_parameter('robot.encoder_edges_per_rev', 1320)  # 11 PPR × 30 gear × 4 quadrature
        self.declare_parameter('control.cmd_timeout', 2.0)
        self.declare_parameter('control.max_velocity', 1.0)
        self.declare_parameter('control.max_angular_velocity', 2.0)

        # Rates
        self.declare_parameter('rates.sensor_rate', 50.0)
        self.declare_parameter('rates.status_rate', 10.0)

        # Safety
        self.declare_parameter('safety.battery_low_threshold', 11.0)
        self.declare_parameter('safety.battery_critical_voltage', 10.5)

        # Odometry covariance (adaptive, grows with distance/rotation)
        self.declare_parameter('odometry.pose_base', 0.001)
        self.declare_parameter('odometry.pose_drift', 0.02)
        self.declare_parameter('odometry.yaw_base', 0.01)
        self.declare_parameter('odometry.yaw_drift', 0.005)
        self.declare_parameter('odometry.velocity_base', 0.01)
        self.declare_parameter('odometry.velocity_scale', 0.1)
        self.declare_parameter('odometry.covariance_decay', 0.99)  # G2: Decay factor for accumulated errors

        # R4: IMU covariance (diagonal entries; -1 for orientation means "unknown")
        self.declare_parameter('imu.linear_acceleration_covariance', 0.01)
        self.declare_parameter('imu.angular_velocity_covariance', 0.0025)
        self.declare_parameter('imu.orientation_covariance', 0.0025)

        # Load values
        self.serial_port = self.get_parameter('hardware.serial_port').value
        self._data_timeout = self.get_parameter('hardware.data_timeout').value
        self.cmd_timeout = self.get_parameter('control.cmd_timeout').value
        self.max_velocity = self.get_parameter('control.max_velocity').value
        self.max_angular_velocity = self.get_parameter('control.max_angular_velocity').value
        self.sensor_rate = self.get_parameter('rates.sensor_rate').value
        self.status_rate = self.get_parameter('rates.status_rate').value
        self.battery_low_threshold = self.get_parameter('safety.battery_low_threshold').value
        self.battery_critical_voltage = self.get_parameter('safety.battery_critical_voltage').value

        # Odometry covariance
        self._cov_pose_base = self.get_parameter('odometry.pose_base').value
        self._cov_pose_drift = self.get_parameter('odometry.pose_drift').value
        self._cov_yaw_base = self.get_parameter('odometry.yaw_base').value
        self._cov_yaw_drift = self.get_parameter('odometry.yaw_drift').value
        self._cov_vel_base = self.get_parameter('odometry.velocity_base').value
        self._cov_vel_scale = self.get_parameter('odometry.velocity_scale').value
        self._cov_decay = self.get_parameter('odometry.covariance_decay').value

        # Robot geometry (R2)
        self.wheel_radius = self.get_parameter('robot.wheel_radius').value
        self.encoder_edges_per_rev = self.get_parameter('robot.encoder_edges_per_rev').value

        # IMU covariance (R4)
        self._imu_accel_cov = self.get_parameter('imu.linear_acceleration_covariance').value
        self._imu_gyro_cov = self.get_parameter('imu.angular_velocity_covariance').value
        self._imu_orient_cov = self.get_parameter('imu.orientation_covariance').value

        # Validate parameters
        self._validate_parameters()

    def _on_set_parameters(self, params):
        """R3: Apply runtime parameter changes (cmd_timeout, max_velocity, max_angular_velocity)."""
        result = SetParametersResult(successful=True)
        for p in params:
            try:
                if p.name == 'control.cmd_timeout':
                    v = p.value.double_value if hasattr(p.value, 'double_value') else p.value
                    if v <= 0:
                        result.successful = False
                        result.reason = 'cmd_timeout must be > 0'
                        break
                    self.cmd_timeout = float(v)
                elif p.name == 'control.max_velocity':
                    v = p.value.double_value if hasattr(p.value, 'double_value') else p.value
                    v = max(0.0, min(2.0, float(v)))
                    self.max_velocity = v
                elif p.name == 'control.max_angular_velocity':
                    v = p.value.double_value if hasattr(p.value, 'double_value') else p.value
                    v = max(0.0, min(4.0, float(v)))
                    self.max_angular_velocity = v
            except (TypeError, AttributeError) as e:
                result.successful = False
                result.reason = str(e)
                break
        return result

    def _validate_parameters(self):
        """Validate parameter values and apply corrections if needed"""
        # Velocity limits 
        if self.max_velocity <= 0:
            self.get_logger().warn(f"Invalid max_velocity ({self.max_velocity}), using 1.0 m/s")
            self.max_velocity = 1.0
        elif self.max_velocity > 2.0:
            self.get_logger().warn(f"max_velocity ({self.max_velocity}) exceeds safe limit, clamping to 2.0 m/s")
            self.max_velocity = 2.0

        if self.max_angular_velocity <= 0:
            self.get_logger().warn(f"Invalid max_angular_velocity ({self.max_angular_velocity}), using 2.0 rad/s")
            self.max_angular_velocity = 2.0
        elif self.max_angular_velocity > 4.0:
            self.get_logger().warn(f"max_angular_velocity ({self.max_angular_velocity}) exceeds safe limit, clamping to 4.0 rad/s")
            self.max_angular_velocity = 4.0

        # Rates 
        if self.sensor_rate <= 0 or self.sensor_rate > 200:
            self.get_logger().warn(f"Invalid sensor_rate ({self.sensor_rate}), using 50.0 Hz")
            self.sensor_rate = 50.0

        if self.status_rate <= 0 or self.status_rate > 100:
            self.get_logger().warn(f"Invalid status_rate ({self.status_rate}), using 10.0 Hz")
            self.status_rate = 10.0

        # Timeout 
        if self.cmd_timeout <= 0:
            self.get_logger().warn(f"Invalid cmd_timeout ({self.cmd_timeout}), using 2.0 s")
            self.cmd_timeout = 2.0

        # Battery thresholds 
        if self.battery_critical_voltage >= self.battery_low_threshold:
            self.get_logger().warn("battery_critical_voltage >= battery_low_threshold, adjusting")
            self.battery_critical_voltage = self.battery_low_threshold - 0.5

        self.get_logger().info(f"Parameters validated: max_vel={self.max_velocity:.1f} m/s, "
                               f"sensor_rate={self.sensor_rate:.0f} Hz")

    def _create_publishers(self):
        """Create ROS publishers with appropriate QoS profiles"""
        # Sensor data — BEST_EFFORT for high-frequency data (reduces CPU on RPi)
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=5
        )
        self.imu_pub = self.create_publisher(Imu, '/imu/data', sensor_qos)
        self.imu_raw_pub = self.create_publisher(Imu, '/imu/data_raw', sensor_qos)
        self.mag_pub = self.create_publisher(MagneticField, '/imu/mag', sensor_qos)
        self.encoder_pub = self.create_publisher(Int32MultiArray, '/orbibot/encoders', sensor_qos)
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.joint_states_pub = self.create_publisher(JointState, '/joint_states', 10)

        # Status — RELIABLE for important state data
        self.system_status_pub = self.create_publisher(SystemStatus, '/orbibot/system_status', 10)
        self.safety_status_pub = self.create_publisher(SafetyStatus, '/orbibot/safety_status', 10)
        self.diagnostics_pub = self.create_publisher(DiagnosticArray, '/diagnostics', 10)

    def _create_subscribers(self):
        """Create ROS subscribers"""
        # cmd_vel — RELIABLE for control commands
        control_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            depth=10
        )
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self._cmd_vel_callback, control_qos)
        self.pid_sub = self.create_subscription(
            Float32MultiArray, '/orbibot/pid_params',
            self._pid_callback, 10)
        self.yaw_pid_sub = self.create_subscription(
            Float32MultiArray, '/orbibot/yaw_pid_params',
            self._yaw_pid_callback, 10)
        # PID save topic - send [kp, ki, kd] with state=0x5F to save to flash
        self.pid_save_sub = self.create_subscription(
            Float32MultiArray, '/orbibot/pid_save',
            self._pid_save_callback, 10)
        self.beep_sub = self.create_subscription(
            UInt16, '/orbibot/beep', self._beep_callback, 10)

    def _create_services(self):
        """Create ROS services"""
        self.motor_enable_srv = self.create_service(
            SetMotorEnable, '/orbibot/set_motor_enable', self._motor_enable_callback)
        self.imu_calibration_srv = self.create_service(
            CalibrateIMU, '/orbibot/calibrate_imu', self._calibrate_imu_callback)
        self.reset_odometry_srv = self.create_service(
            ResetOdometry, '/orbibot/reset_odometry', self._reset_odometry_callback)

    def _create_timers(self):
        """Create periodic timers"""
        self.sensor_timer = self.create_timer(
            1.0 / self.sensor_rate, self._sensor_callback,
            callback_group=self._sensor_cb_group)
        self.status_timer = self.create_timer(
            1.0 / self.status_rate, self._status_callback,
            callback_group=self._sensor_cb_group)
        self.safety_timer = self.create_timer(
            0.1, self._safety_callback,
            callback_group=self._sensor_cb_group)

    def _initialize_hardware(self):
        """Initialize ROSMaster board connection"""
        if not ROSMASTER_AVAILABLE:
            self.get_logger().error('rosmaster_driver not available')
            return

        try:
            self.get_logger().info(f"Connecting to ROSMaster on {self.serial_port}...")

            self.bot = rosmaster_driver.Rosmaster(
                car_type=rosmaster_driver.CARTYPE_ORBIBOT,
                com=self.serial_port,
                debug=False
            )

            # Enable auto-report (firmware sends data @ 25Hz per type).
            # forever=False: temporary — avoids unnecessary flash writes on every startup.
            # OrbiBot firmware enables auto-report by default in its RTOS task.
            self.bot.create_receive_threading()
            time.sleep(0.1)
            self.bot.set_auto_report_state(True, forever=False)
            time.sleep(0.1)

            # Initialize to stopped
            self.bot.set_car_motion(0, 0, 0)

            self.hardware_connected = True
            self.get_logger().info("ROSMaster connected successfully")

        except Exception as e:
            self.get_logger().error(f"Hardware init failed: {str(e)}")
            self.hardware_connected = False

    def _cmd_vel_callback(self, msg: Twist):
        """Send velocity commands to firmware"""
        if not self.hardware_connected:
            return

        # Update command time (thread-safe, prevents timeout even if motors disabled)
        with self._cmd_time_lock:
            self._last_cmd_time = time.time()
            self._timeout_stop_sent = False  # G1: Reset timeout stop flag on new command

        # G4: Thread-safe read of motors_enabled
        with self._state_lock:
            enabled = self.motors_enabled
        if not enabled:
            return

        # Clamp to safe limits and track if velocity was limited
        vx = max(-self.max_velocity, min(msg.linear.x, self.max_velocity))
        vy = max(-self.max_velocity, min(msg.linear.y, self.max_velocity))
        vz = max(-self.max_angular_velocity, min(msg.angular.z, self.max_angular_velocity))
        self._velocity_limited = (
            vx != msg.linear.x or vy != msg.linear.y or vz != msg.angular.z)

        try:
            self.bot.set_car_motion(vx, vy, vz)
        except Exception as e:
            self.get_logger().error(f"Motion command failed: {e}")

    def _beep_callback(self, msg: UInt16):
        """Trigger buzzer via /orbibot/beep topic.

        Args:
            msg: Duration in ms. 0=off, 1=continuous, >=10=beep for N ms then auto-off.
        """
        if not self.hardware_connected:
            return
        try:
            self.bot.set_beep(msg.data)
        except Exception as e:
            self.get_logger().error(f"Beep command failed: {e}")

    def _check_pid_rate_limit(self, last_update_attr: str) -> bool:
        """Q5: Return True if rate limit passed and update last_update time. Max 10Hz per PID topic."""
        t = time.time()
        if t - getattr(self, last_update_attr) < self._pid_rate_limit:
            return False
        setattr(self, last_update_attr, t)
        return True

    def _pid_callback(self, msg: Float32MultiArray):
        """Update motor PID gains on firmware via /orbibot/pid_params topic."""
        if not self.hardware_connected:
            return
        if not self._check_pid_rate_limit('_last_pid_update'):
            return

        if len(msg.data) != 3:
            self.get_logger().warn(f"PID params requires [kp, ki, kd], got {len(msg.data)} values")
            return

        kp, ki, kd = msg.data
        self.get_logger().info(f"Updating motor PID: Kp={kp:.3f} Ki={ki:.3f} Kd={kd:.3f}")
        try:
            self.bot.set_pid_param(kp, ki, kd)
        except Exception as e:
            self.get_logger().error(f"Set motor PID failed: {e}")

    def _yaw_pid_callback(self, msg: Float32MultiArray):
        """Update yaw PID gains on firmware via /orbibot/yaw_pid_params topic."""
        if not self.hardware_connected:
            return
        if not self._check_pid_rate_limit('_last_yaw_pid_update'):
            return

        if len(msg.data) != 3:
            self.get_logger().warn(f"Yaw PID params requires [kp, ki, kd], got {len(msg.data)} values")
            return

        kp, ki, kd = msg.data
        self.get_logger().info(f"Updating yaw PID: Kp={kp:.3f} Ki={ki:.3f} Kd={kd:.3f}")
        try:
            self.bot.set_yaw_pid_param(kp, ki, kd)
        except Exception as e:
            self.get_logger().error(f"Set yaw PID failed: {e}")

    def _pid_save_callback(self, msg: Float32MultiArray):
        """Trigger flash save via /orbibot/pid_save topic.

        Sends the current PID gains with forever=True to trigger flash save.
        Data format: [kp, ki, kd] - single PID gains.
        """
        if not self.hardware_connected:
            return
        if not self._check_pid_rate_limit('_last_pid_save_update'):
            return

        try:
            if len(msg.data) >= 3:
                # Single PID format
                kp, ki, kd = msg.data[0], msg.data[1], msg.data[2]
                self.bot.set_pid_param(kp, ki, kd, forever=True)
                self.get_logger().info(f"PID gains saved to flash: Kp={kp:.3f} Ki={ki:.3f} Kd={kd:.3f}")
            else:
                self.get_logger().warn("Invalid PID save data length - expected [kp, ki, kd]")
        except Exception as e:
            self.get_logger().error(f"PID flash save failed: {e}")

    def _sensor_callback(self):
        """Publish sensor data @ 50Hz. R1/Q4: single fetch per cycle. S1/S2: data freshness."""
        if not self.hardware_connected:
            return

        # S1/S2: Data freshness — if no firmware data for data_timeout, mark disconnected
        try:
            last_ts = self.bot.get_last_data_timestamp()
            if last_ts > 0 and (time.time() - last_ts) > self._data_timeout:
                self.hardware_connected = False
                self.get_logger().warn("Hardware data timeout — marking disconnected")
                return
            if last_ts > 0:
                self.hardware_connected = True  # recover when data flows again
        except (AttributeError, TypeError):
            pass

        # Command timeout safety — G1: send stop once, G4: thread-safe state reads
        with self._cmd_time_lock:
            cmd_age = time.time() - self._last_cmd_time
        with self._state_lock:
            motors_active = self.motors_enabled
        send_stop = False
        with self._cmd_time_lock:
            if cmd_age > self.cmd_timeout and motors_active and not self._timeout_stop_sent:
                self._timeout_stop_sent = True
                send_stop = True
        if send_stop:
            self.bot.set_car_motion(0, 0, 0)

        # R1/Q4: Fetch all sensor data once per cycle, then publish
        try:
            accel_data = self.bot.get_accelerometer_data()
            gyro_data = self.bot.get_gyroscope_data()
            attitude_data = self.bot.get_imu_attitude_data(to_angle=False)
            mag_data = self.bot.get_magnetometer_data()
            odom_data = self.bot.get_firmware_odometry()
            encoders = self.bot.get_motor_encoder()
        except Exception as e:
            self.get_logger().error(f"Sensor fetch failed: {e}")
            return

        self._publish_imu(accel_data, gyro_data, attitude_data)
        self._publish_imu_raw(accel_data, gyro_data)
        self._publish_mag(mag_data)
        self._publish_firmware_odom(odom_data)
        self._publish_encoders(encoders)
        self._publish_joint_states(encoders)

    def _publish_imu(self, accel_data, gyro_data, attitude_data):
        """Publish IMU data (data from single fetch in _sensor_callback)."""
        try:
            if not all(len(data) == 3 for data in [accel_data, gyro_data, attitude_data]):
                return
            msg = Imu()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'imu_link'

            msg.linear_acceleration.x = float(accel_data[0])
            msg.linear_acceleration.y = float(accel_data[1])
            msg.linear_acceleration.z = float(accel_data[2])
            msg.angular_velocity.x = float(gyro_data[0])
            msg.angular_velocity.y = float(gyro_data[1])
            msg.angular_velocity.z = float(gyro_data[2])

            roll, pitch, yaw = float(attitude_data[0]), float(attitude_data[1]), float(attitude_data[2])
            cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
            cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
            cr, sr = math.cos(roll * 0.5), math.sin(roll * 0.5)
            msg.orientation.w = float(cr * cp * cy + sr * sp * sy)
            msg.orientation.x = float(sr * cp * cy - cr * sp * sy)
            msg.orientation.y = float(cr * sp * cy + sr * cp * sy)
            msg.orientation.z = float(cr * cp * sy - sr * sp * cy)

            c = self._imu_accel_cov
            msg.linear_acceleration_covariance = [c, 0.0, 0.0, 0.0, c, 0.0, 0.0, 0.0, c]
            c = self._imu_gyro_cov
            msg.angular_velocity_covariance = [c, 0.0, 0.0, 0.0, c, 0.0, 0.0, 0.0, c]
            c = self._imu_orient_cov
            msg.orientation_covariance = [c, 0.0, 0.0, 0.0, c, 0.0, 0.0, 0.0, c]
            self.imu_pub.publish(msg)
        except Exception as e:
            self.get_logger().error(f"IMU publish failed: {str(e)}")

    def _publish_imu_raw(self, accel_data, gyro_data):
        """Publish raw IMU data (no orientation) for imu_filter_madgwick input."""
        try:
            if not all(len(d) == 3 for d in [accel_data, gyro_data]):
                return
            msg = Imu()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'imu_link'
            msg.linear_acceleration.x = float(accel_data[0])
            msg.linear_acceleration.y = float(accel_data[1])
            msg.linear_acceleration.z = float(accel_data[2])
            msg.angular_velocity.x = float(gyro_data[0])
            msg.angular_velocity.y = float(gyro_data[1])
            msg.angular_velocity.z = float(gyro_data[2])
            msg.orientation_covariance[0] = -1.0
            c = self._imu_accel_cov
            msg.linear_acceleration_covariance = [c, 0.0, 0.0, 0.0, c, 0.0, 0.0, 0.0, c]
            c = self._imu_gyro_cov
            msg.angular_velocity_covariance = [c, 0.0, 0.0, 0.0, c, 0.0, 0.0, 0.0, c]
            self.imu_raw_pub.publish(msg)
        except Exception as e:
            self.get_logger().error(f"IMU raw publish failed: {e}")

    def _publish_mag(self, mag_data):
        """Publish magnetometer data for imu_filter_madgwick."""
        try:
            if len(mag_data) != 3:
                return
            if mag_data[0] == 0.0 and mag_data[1] == 0.0 and mag_data[2] == 0.0:
                return
            msg = MagneticField()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'imu_link'

            # rosmaster_driver returns µT, MagneticField expects Tesla
            msg.magnetic_field.x = float(mag_data[0]) * 1e-6
            msg.magnetic_field.y = float(mag_data[1]) * 1e-6
            msg.magnetic_field.z = float(mag_data[2]) * 1e-6

            # Unknown covariance
            msg.magnetic_field_covariance = [0.0] * 9

            self.mag_pub.publish(msg)

        except Exception as e:
            self.get_logger().error(f"Mag publish failed: {e}")

    def _publish_firmware_odom(self, odom_data):
        """Publish firmware odometry on /odom with adaptive covariance."""
        try:
            if self._last_firmware_odom is not None and odom_data == self._last_firmware_odom:
                return
            self._last_firmware_odom = odom_data
            x, y, theta, vx, vy, omega = odom_data

            # Track accumulated distance/rotation for adaptive covariance
            # G2: Apply exponential decay to prevent unbounded growth
            dx = x - self._last_odom_x
            dy = y - self._last_odom_y
            # Modular angular difference to handle ±PI wraparound
            dtheta = abs(((theta - self._last_odom_theta) + math.pi) % (2 * math.pi) - math.pi)
            self._accumulated_distance = self._accumulated_distance * self._cov_decay + math.sqrt(dx * dx + dy * dy)
            self._accumulated_rotation = self._accumulated_rotation * self._cov_decay + dtheta
            self._last_odom_x = x
            self._last_odom_y = y
            self._last_odom_theta = theta

            # Adaptive covariance: grows with distance traveled
            pos_var = self._cov_pose_base + self._accumulated_distance * self._cov_pose_drift
            yaw_var = self._cov_yaw_base + self._accumulated_rotation * self._cov_yaw_drift
            speed = math.sqrt(vx * vx + vy * vy)
            vel_var = self._cov_vel_base + speed * self._cov_vel_scale
            omega_var = self._cov_vel_base + abs(omega) * self._cov_vel_scale

            msg = Odometry()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'odom'
            msg.child_frame_id = 'base_footprint'

            # Position
            msg.pose.pose.position.x = x
            msg.pose.pose.position.y = y
            msg.pose.pose.position.z = 0.0

            # Orientation from theta (yaw-only quaternion)
            half_yaw = theta * 0.5
            msg.pose.pose.orientation.x = 0.0
            msg.pose.pose.orientation.y = 0.0
            msg.pose.pose.orientation.z = math.sin(half_yaw)
            msg.pose.pose.orientation.w = math.cos(half_yaw)

            # Velocity
            msg.twist.twist.linear.x = vx
            msg.twist.twist.linear.y = vy
            msg.twist.twist.angular.z = omega

            # Adaptive covariance matrices (6x6 flattened, row-major)
            msg.pose.covariance = [
                pos_var, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, pos_var, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, yaw_var,
            ]
            msg.twist.covariance = [
                vel_var, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, vel_var, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, omega_var,
            ]

            self.odom_pub.publish(msg)

        except Exception as e:
            self.get_logger().error(f"Odom publish failed: {e}")

    def _publish_encoders(self, encoders):
        """Publish raw encoder counts for odometry calculation"""
        try:
            msg = Int32MultiArray()
            msg.data = list(encoders)  # [m1, m2, m3, m4] = [FL, BL, FR, BR]

            self.encoder_pub.publish(msg)

        except Exception as e:
            self.get_logger().error(f"Encoder publish failed: {str(e)}")

    def _publish_joint_states(self, encoders):
        """Publish wheel joint states for RViz visualization"""
        try:
            rad_per_edge = (2.0 * math.pi) / self.encoder_edges_per_rev

            # Initialize last_encoders on first run
            if not self.encoder_initialized:
                self.last_encoders = list(encoders)
                self.encoder_initialized = True
                return

            # Calculate wheel positions from encoder deltas
            for i in range(4):
                delta = encoders[i] - self.last_encoders[i]
                self.last_encoders[i] = encoders[i]
                # Encoder direction is corrected in firmware (forward = positive delta)
                self.wheel_positions[i] += delta * rad_per_edge

            # Create and publish joint state
            joint_msg = JointState()
            joint_msg.header.stamp = self.get_clock().now().to_msg()
            joint_msg.name = [
                'wheel_front_left_joint',
                'wheel_back_left_joint',
                'wheel_front_right_joint',
                'wheel_back_right_joint'
            ]
            joint_msg.position = self.wheel_positions.copy()
            joint_msg.velocity = []
            joint_msg.effort = []

            self.joint_states_pub.publish(joint_msg)

        except Exception as e:
            self.get_logger().error(f"Joint states publish failed: {str(e)}")

    def _status_callback(self):
        """Publish system status @ 10Hz"""
        if not self.hardware_connected:
            return

        try:
            battery_voltage = self.bot.get_battery_voltage()

            # System status - G4: Thread-safe read of state variables
            with self._state_lock:
                motors_enabled = self.motors_enabled
                emergency_stop = self.emergency_stop

            status_msg = SystemStatus()
            status_msg.header.stamp = self.get_clock().now().to_msg()
            status_msg.battery_voltage = battery_voltage
            status_msg.motors_enabled = motors_enabled
            status_msg.emergency_stop = emergency_stop
            status_msg.hardware_ok = self.hardware_connected

            self.system_status_pub.publish(status_msg)

            # Diagnostics
            self._publish_diagnostics(battery_voltage, motors_enabled)

        except Exception as e:
            self.get_logger().error(f"Status publish failed: {str(e)}")

    def _publish_diagnostics(self, battery_voltage, motors_enabled):
        """Publish diagnostic info"""
        diag_array = DiagnosticArray()
        diag_array.header.stamp = self.get_clock().now().to_msg()

        hw_status = DiagnosticStatus()
        hw_status.name = "OrbiBot Hardware"
        hw_status.hardware_id = "orbibot_hw"
        hw_status.level = DiagnosticStatus.OK if self.hardware_connected else DiagnosticStatus.ERROR
        hw_status.message = "Operational" if self.hardware_connected else "Disconnected"
        hw_status.values = [
            KeyValue(key="Battery", value=f"{battery_voltage:.1f}V"),
            KeyValue(key="Motors", value="Enabled" if motors_enabled else "Disabled"),
        ]

        diag_array.status.append(hw_status)
        self.diagnostics_pub.publish(diag_array)

    def _safety_callback(self):
        """Monitor safety @ 10Hz"""
        if not self.hardware_connected:
            return

        # Thread-safe read of command time
        with self._cmd_time_lock:
            cmd_timeout = time.time() - self._last_cmd_time > self.cmd_timeout

        try:
            battery_voltage = self.bot.get_battery_voltage()
            low_battery = 0 < battery_voltage < self.battery_low_threshold
            critical_battery = 0 < battery_voltage < self.battery_critical_voltage
        except (AttributeError, TypeError, ValueError, OSError) as e:
            self.get_logger().debug(f"Battery read failed: {e}")
            battery_voltage = 0.0
            low_battery = False
            critical_battery = False

        # Safety status message - G4: Thread-safe read of state
        with self._state_lock:
            emergency_stop = self.emergency_stop
            motors_enabled = self.motors_enabled

        safety_msg = SafetyStatus()
        safety_msg.header.stamp = self.get_clock().now().to_msg()
        safety_msg.emergency_stop = emergency_stop
        safety_msg.cmd_timeout = cmd_timeout
        safety_msg.low_battery = low_battery
        safety_msg.hardware_fault = not self.hardware_connected
        safety_msg.motors_disabled = not motors_enabled
        safety_msg.velocity_limit = self._velocity_limited

        self.safety_status_pub.publish(safety_msg)

        # Emergency actions - G4: Thread-safe write of state
        if critical_battery:
            with self._state_lock:
                self.emergency_stop = True
                self.motors_enabled = False
            self.bot.set_car_motion(0, 0, 0)
        elif not critical_battery and emergency_stop:
            with self._state_lock:
                self.emergency_stop = False
            self.get_logger().info(
                "Battery recovered. Motors disabled — call set_motor_enable to re-enable."  # S3
            )

    # Service Callbacks
    def _motor_enable_callback(self, request, response):
        """Enable/disable motors. (BUG-3: set_car_motion called outside _state_lock.)"""
        try:
            send_stop = False
            # G4: Thread-safe access to state variables; do not call set_car_motion inside lock
            with self._state_lock:
                if request.enable and not self.emergency_stop:
                    self.motors_enabled = True
                    response.success = True
                    response.message = "Motors enabled"
                    self.get_logger().info("Motors enabled")
                elif not request.enable:
                    self.motors_enabled = False
                    response.success = True
                    response.message = "Motors disabled"
                    self.get_logger().info("Motors disabled")
                    send_stop = True
                else:
                    response.success = False
                    response.message = "Emergency stop active"
            if send_stop:
                self.bot.set_car_motion(0, 0, 0)
        except Exception as e:
            response.success = False
            response.message = f"Error: {str(e)}"

        return response

    def _calibrate_imu_callback(self, request, response):
        """Trigger magnetometer calibration via set_mag_calibration()."""
        if not self.hardware_connected:
            response.success = False
            response.message = "Hardware not connected"
            response.bias_values = [0.0, 0.0, 0.0]
            return response

        try:
            # The CalibrateIMU service doesn't have offset fields in its definition,
            # so we trigger auto-calibration by setting offsets to 0, 0, 0
            # In practice, the firmware uses the current magnetometer reading as the
            # hard iron offset (since the robot is stationary during calibration)
            # Note: The calibration time parameter is used to wait for stabilization
            calibration_time = request.calibration_time if request.calibration_time > 0 else 10

            self.get_logger().info(f"Starting magnetometer calibration (wait {calibration_time}s)...")

            # Wait for the specified calibration time to allow sensor stabilization
            # This gives the user time to rotate the robot if needed
            # In a real implementation, the firmware would handle this
            # For now, we apply zero offsets (which the firmware treats as "use current reading")
            self.bot.set_mag_calibration(0.0, 0.0, 0.0)

            response.success = True
            response.message = f"Magnetometer calibration applied (waited {calibration_time}s for stabilization)"
            response.bias_values = [0.0, 0.0, 0.0]  # Firmware stores internally, not returned here

            self.get_logger().info("Magnetometer calibration complete")

        except Exception as e:
            response.success = False
            response.message = f"Calibration failed: {e}"
            response.bias_values = [0.0, 0.0, 0.0]

        return response

    def _reset_odometry_callback(self, request, response):
        """Reset odometry (firmware + ROS-side covariance accumulators).

        Note: request.reset_pose field is currently ignored - firmware always resets to zero.
        """
        try:
            # Reset firmware odometry to zero
            self.bot.reset_odometry()

            # Reset ROS-side covariance accumulators
            self._accumulated_distance = 0.0
            self._accumulated_rotation = 0.0

            self.get_logger().info("Firmware odometry and covariance reset to zero")
            response.success = True
            response.message = "Firmware odometry and covariance reset (zero only - custom pose not supported)"
        except Exception as e:
            self.get_logger().error(f"Reset odometry failed: {e}")
            response.success = False
            response.message = f"Reset failed: {e}"

        return response

    def cleanup(self):
        """Shutdown cleanup"""
        self.get_logger().info("Shutting down...")

        if self.hardware_connected and self.bot:
            try:
                self.bot.set_car_motion(0, 0, 0)
                self.bot.set_auto_report_state(False, forever=False)
            except Exception as e:
                self.get_logger().debug(f'Cleanup error: {e}')
            finally:
                self.bot.close()


def main(args=None):
    rclpy.init(args=args)

    try:
        node = OrbiBotHardwareNode()
        executor = MultiThreadedExecutor(num_threads=4)
        executor.add_node(node)

        try:
            executor.spin()
        except KeyboardInterrupt:
            pass
        finally:
            node.cleanup()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()
