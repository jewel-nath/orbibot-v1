/**
 * Shared constants for the OrbiBot web GUI.
 *
 * Topic names, message types, robot parameters, and UI defaults.
 * Values must match the ROS 2 node configuration in orbibot_hardware,
 * orbibot_sensors, and orbibot_exploration.
 */

// -- ROS topic names --

export const ROS_TOPICS = {
  cmdVel: '/cmd_vel',
  odom: '/odom',
  odomFiltered: '/odometry/filtered',
  imu: '/imu/data',
  imuRaw: '/imu/data_raw',
  imuMag: '/imu/mag',
  scan: '/scan',
  jointStates: '/joint_states',
  diagnostics: '/diagnostics',
  systemStatus: '/orbibot/system_status',
  systemStatusEnriched: '/orbibot/system_status_enriched',
  safetyStatus: '/orbibot/safety_status',
  encoders: '/orbibot/encoders',
  pidParams: '/orbibot/pid_params',
  pidSave: '/orbibot/pid_save',
  yawPidParams: '/orbibot/yaw_pid_params',
  yawPidSave: '/orbibot/yaw_pid_save',
  beep: '/orbibot/beep',
  explorationCommand: '/orbibot/exploration/command',
  explorationStatus: '/orbibot/exploration/status',
  explorationFrontiers: '/orbibot/exploration/frontiers',
} as const;

// -- ROS message type strings (for roslib) --

export const ROS_MESSAGE_TYPES = {
  twist: 'geometry_msgs/Twist',
  odometry: 'nav_msgs/Odometry',
  occupancyGrid: 'nav_msgs/OccupancyGrid',
  laserScan: 'sensor_msgs/LaserScan',
  imu: 'sensor_msgs/Imu',
  jointState: 'sensor_msgs/JointState',
  magneticField: 'sensor_msgs/MagneticField',
  diagnosticArray: 'diagnostic_msgs/DiagnosticArray',
  uint16: 'std_msgs/UInt16',
  int32MultiArray: 'std_msgs/Int32MultiArray',
  systemStatus: 'orbibot_msgs/SystemStatus',
  safetyStatus: 'orbibot_msgs/SafetyStatus',
  encoderStamped: 'orbibot_msgs/EncoderStamped',
} as const;

// -- Motor mapping (matches firmware M1-M4 order) --

export const MOTOR_MAPPING = [
  { id: 1, name: 'M1', position: 'front_left', abbreviation: 'FL' },
  { id: 2, name: 'M2', position: 'back_left', abbreviation: 'BL' },
  { id: 3, name: 'M3', position: 'front_right', abbreviation: 'FR' },
  { id: 4, name: 'M4', position: 'back_right', abbreviation: 'BR' },
] as const;

// -- Robot physical parameters --

export const ROBOT_PARAMS = {
  defaultLinearVel: 0.5,   // m/s max forward/strafe
  defaultAngularVel: 1.9,  // rad/s max rotation
} as const;

// -- Battery thresholds (4S LiFePO4) --

export const BATTERY_PARAMS = {
  full: 14.6,              // fully charged
  lowThreshold: 11.0,      // warning
  criticalThreshold: 10.5, // emergency stop
} as const;

// -- UI defaults --

export const UI_CONSTANTS = {
  defaultSpeedPercent: 50,
  minSpeedPercent: 10,
  maxSpeedPercent: 100,
  publishRate: 20,  // Hz for button/keyboard velocity publishing
} as const;

// -- WebSocket (rosbridge) connection --

export const WS_CONFIG = {
  defaultUrl: `ws://${window.location.hostname}:9090`,
  maxReconnectAttempts: 10,
  reconnectDelay: 3000,  // ms between retries
} as const;
