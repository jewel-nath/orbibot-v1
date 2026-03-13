/**
 * TypeScript type definitions for ROS messages
 * These match the ROS 2 message definitions used by OrbiBot
 */

// ============================================================================
// Standard ROS Message Types
// ============================================================================

export interface Header {
  stamp: {
    sec: number;
    nanosec: number;
  };
  frame_id: string;
}

// geometry_msgs/Vector3
export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

// geometry_msgs/Quaternion
export interface Quaternion {
  x: number;
  y: number;
  z: number;
  w: number;
}

// geometry_msgs/Twist
export interface Twist {
  linear: Vector3;
  angular: Vector3;
}

// geometry_msgs/Pose
export interface Pose {
  position: Vector3;
  orientation: Quaternion;
}

// geometry_msgs/PoseWithCovariance
export interface PoseWithCovariance {
  pose: Pose;
  covariance: number[]; // 6x6 matrix as 36-element array
}

// geometry_msgs/TwistWithCovariance
export interface TwistWithCovariance {
  twist: Twist;
  covariance: number[]; // 6x6 matrix as 36-element array
}

// ============================================================================
// nav_msgs
// ============================================================================

// nav_msgs/Odometry
export interface Odometry {
  header: Header;
  child_frame_id: string;
  pose: PoseWithCovariance;
  twist: TwistWithCovariance;
}

// nav_msgs/OccupancyGrid
export interface OccupancyGrid {
  header: Header;
  info: {
    map_load_time: {
      sec: number;
      nanosec: number;
    };
    resolution: number;   // m/cell
    width: number;        // cells
    height: number;       // cells
    origin: Pose;
  };
  data: number[];         // [0-100] occupancy, -1 unknown
}

// ============================================================================
// sensor_msgs
// ============================================================================

// sensor_msgs/Imu
export interface Imu {
  header: Header;
  orientation: Quaternion;
  orientation_covariance: number[]; // 3x3 matrix as 9-element array
  angular_velocity: Vector3;
  angular_velocity_covariance: number[]; // 3x3 matrix as 9-element array
  linear_acceleration: Vector3;
  linear_acceleration_covariance: number[]; // 3x3 matrix as 9-element array
}

// sensor_msgs/LaserScan
export interface LaserScan {
  header: Header;
  angle_min: number;      // radians
  angle_max: number;      // radians
  angle_increment: number;// radians
  time_increment: number; // seconds
  scan_time: number;      // seconds
  range_min: number;      // meters
  range_max: number;      // meters
  ranges: number[];       // meters (one per angle)
  intensities: number[];  // intensity values
}

// ============================================================================
// Custom OrbiBot Messages (orbibot_msgs)
// ============================================================================

// orbibot_msgs/SystemStatus (matches actual msg definition)
export interface SystemStatus {
  header: Header;
  battery_voltage: number;      // Volts
  motors_enabled: boolean;      // True if motors are enabled
  emergency_stop: boolean;      // True if emergency stop is active
  hardware_ok: boolean;         // True if all hardware is responding
}

// orbibot_msgs/SafetyStatus (matches SafetyStatus.msg)
export interface SafetyStatus {
  header: Header;
  emergency_stop: boolean;
  cmd_timeout: boolean;
  low_battery: boolean;
  hardware_fault: boolean;
  velocity_limit: boolean;
  temperature_limit: boolean;
  motors_disabled: boolean;
  fault_code: number;
}

// std_msgs/Int32MultiArray (actual type for /orbibot/encoders)
export interface EncoderStamped {
  layout: {
    dim: unknown[];
    data_offset: number;
  };
  data: number[];               // [M1, M2, M3, M4] raw encoder counts
}

// ============================================================================
// UI-Specific Types
// ============================================================================

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface RosConnectionStatus {
  state: ConnectionState;
  url: string;
  error?: string;
  lastConnected?: Date;
}

export interface VelocityCommand {
  linear_x: number;  // m/s (forward/backward)
  linear_y: number;  // m/s (strafe left/right)
  angular_z: number; // rad/s (rotation)
}

export interface BatteryStatus {
  voltage: number;
  percentage: number;
  status: 'full' | 'normal' | 'low' | 'critical';
}

export interface MotorState {
  id: number;        // 1-4
  name: string;      // M1-M4
  position: string;  // Front-Left, etc.
  abbreviation: string; // FL, BL, etc.
  enabled: boolean;
  current: number;   // Amps
  temperature: number; // Celsius
  encoderCount: number;
  encoderVelocity: number;
}

export interface IMUData {
  roll: number;   // degrees
  pitch: number;  // degrees
  yaw: number;    // degrees
  angular_velocity: Vector3;
  linear_acceleration?: Vector3;  // m/s²
}

export interface OdometryData {
  x: number;      // meters
  y: number;      // meters
  theta: number;  // degrees
  vx: number;     // m/s
  vy: number;     // m/s
  vtheta: number; // rad/s
}
