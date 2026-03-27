/**
 * Shared math utilities for sensor data conversion.
 */

interface Quaternion {
  x: number;
  y: number;
  z: number;
  w: number;
}

interface EulerAngles {
  roll: number;
  pitch: number;
  yaw: number;
}

/**
 * Convert a quaternion to Euler angles (degrees).
 *
 * Uses the ZYX convention (yaw-pitch-roll), which matches ROS orientation output.
 */
export function quaternionToEuler(q: Quaternion): EulerAngles {
  // Roll (x-axis rotation)
  const sinr_cosp = 2 * (q.w * q.x + q.y * q.z);
  const cosr_cosp = 1 - 2 * (q.x * q.x + q.y * q.y);
  const roll = Math.atan2(sinr_cosp, cosr_cosp);

  // Pitch (y-axis rotation) — clamped to ±90° to avoid gimbal lock artefacts
  const sinp = 2 * (q.w * q.y - q.z * q.x);
  const pitch = Math.abs(sinp) >= 1
    ? Math.sign(sinp) * (Math.PI / 2)
    : Math.asin(sinp);

  // Yaw (z-axis rotation)
  const siny_cosp = 2 * (q.w * q.z + q.x * q.y);
  const cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z);
  const yaw = Math.atan2(siny_cosp, cosy_cosp);

  const toDeg = 180 / Math.PI;
  return {
    roll: roll * toDeg,
    pitch: pitch * toDeg,
    yaw: yaw * toDeg,
  };
}

/**
 * Extract yaw (z-axis rotation) from quaternion in radians.
 */
export function quaternionToYaw(q: Quaternion): number {
  const siny_cosp = 2 * (q.w * q.z + q.x * q.y);
  const cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z);
  return Math.atan2(siny_cosp, cosy_cosp);
}
