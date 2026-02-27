#!/usr/bin/env python3
"""
Advanced Mecanum Controller for OrbiBot - Showcases All Holonomic Capabilities
Demonstrates: sideways, diagonal, pivot, rotate, crab movement, circle patterns
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist
from orbibot_msgs.srv import SetMotorEnable
import math
import time
from enum import Enum


# PS4/PS5 DualSense axis mapping
LEFT_STICK_X = 0
LEFT_STICK_Y = 1
L2_AXIS = 2
RIGHT_STICK_X = 3
RIGHT_STICK_Y = 4
R2_AXIS = 5

# D-pad axes (PS4/PS5) - some controllers report D-pad as axes
DPAD_X = 6   # D-pad horizontal (-1=left, 1=right)
DPAD_Y = 7   # D-pad vertical (1=up, -1=down)

# D-pad as buttons (alternative mapping if axes don't work)
DPAD_UP_BTN = 13
DPAD_DOWN_BTN = 14
DPAD_LEFT_BTN = 15
DPAD_RIGHT_BTN = 16

# PS4/PS5 DualSense button mapping
X_BUTTON = 0
CIRCLE_BUTTON = 1
TRIANGLE_BUTTON = 2
SQUARE_BUTTON = 3
L1_BUTTON = 4
R1_BUTTON = 5
L2_BUTTON = 6
R2_BUTTON = 7
SHARE_BUTTON = 8
OPTIONS_BUTTON = 9
L3_BUTTON = 10
R3_BUTTON = 11
PS_BUTTON = 12


class MecanumMode(Enum):
    """Mecanum movement modes"""
    NORMAL = 0      # Free control (forward/back + strafe + turn)
    STRAFE = 1      # Pure sideways movement only
    DIAGONAL = 2    # 45-degree diagonal movements
    ROTATE = 3      # Pure rotation in place (pivot)
    CRAB = 4        # Rotate while strafing
    CIRCLE = 5      # Drive in circles (simultaneous forward + turn)
    PIVOT_STRAFE = 6  # Strafe + rotate simultaneously


class Controller(Node):
    """Advanced PS4/PS5 DualSense controller with full mecanum capabilities"""

    def __init__(self):
        super().__init__('controller')

        # Speed control parameters
        self.declare_parameter('max_linear_speed', 0.3)
        self.declare_parameter('max_angular_speed', 1.0)
        self.declare_parameter('deadzone', 0.08)
        self.declare_parameter('enable_motors_on_start', False)

        self.max_linear = self.get_parameter('max_linear_speed').value
        self.max_angular = self.get_parameter('max_angular_speed').value
        self.deadzone = self.get_parameter('deadzone').value
        self.enable_motors_on_start = self.get_parameter('enable_motors_on_start').value

        # Control state
        self.motor_enabled = False
        self.speed_gear = 1.0  # Speed multiplier (1.0, 0.66, 0.33)
        self.angular_gear = 1.0
        self.mecanum_mode = MecanumMode.NORMAL
        self.last_button_time = {}

        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Subscribers
        self.joy_sub = self.create_subscription(Joy, '/joy', self.joy_callback, 10)

        # Service clients
        self.motor_enable_client = self.create_client(
            SetMotorEnable, '/orbibot/set_motor_enable'
        )

        # Initialize button debounce
        for i in range(20):
            self.last_button_time[i] = 0.0

        if self.enable_motors_on_start:
            self.enable_motors(True)

        self.print_controls()
        self.print_mode_info()

    def print_controls(self):
        """Print controller layout"""
        self.get_logger().info("Advanced Mecanum Controller Ready")
        self.get_logger().info("MOVEMENT: Left Stick (move) + Right Stick X (rotate)")
        self.get_logger().info("MODE SELECTION (D-Pad): UP=Normal, RIGHT=Strafe, DOWN=Diagonal, LEFT=Rotate")
        self.get_logger().info("SPECIAL: R3=Crab, L3=Circle")
        self.get_logger().info("CONTROL: R2=Move, L1=Toggle motors, Triangle/X=Speed, Square/Circle=Angular, Share=E-Stop")

    def print_mode_info(self):
        """Print current mode information"""
        mode_descriptions = {
            MecanumMode.NORMAL: "NORMAL - Free control (forward/back + strafe + turn)",
            MecanumMode.STRAFE: "STRAFE - Pure sideways movement only",
            MecanumMode.DIAGONAL: "DIAGONAL - 45 deg diagonal movements",
            MecanumMode.ROTATE: "ROTATE - Pure rotation in place (pivot)",
            MecanumMode.CRAB: "CRAB - Rotate while strafing",
            MecanumMode.CIRCLE: "CIRCLE - Drive in arcs (forward + turn)",
            MecanumMode.PIVOT_STRAFE: "PIVOT_STRAFE - Strafe + rotate combined"
        }
        self.get_logger().info(f"Mode: {mode_descriptions[self.mecanum_mode]}")
        self.get_logger().info(f"Speed: {self.speed_gear:.0%} | Angular: {self.angular_gear:.0%}")

    def apply_deadzone(self, value):
        """Apply deadzone with proper scaling"""
        if abs(value) < self.deadzone:
            return 0.0
        sign = 1 if value > 0 else -1
        return sign * (abs(value) - self.deadzone) / (1.0 - self.deadzone)

    def button_pressed(self, button_id, msg):
        """Check if button was just pressed (debounced)"""
        current_time = time.time()
        if button_id >= len(msg.buttons) or msg.buttons[button_id] == 0:
            return False

        if current_time - self.last_button_time.get(button_id, 0) > 0.3:
            self.last_button_time[button_id] = current_time
            return True
        return False

    def axis_activated(self, axis_id, msg, threshold=0.5):
        """Check if axis exceeds threshold (for D-pad)"""
        if axis_id >= len(msg.axes):
            return False
        return abs(msg.axes[axis_id]) > threshold

    def enable_motors(self, enable):
        """Enable or disable motors via async service call"""
        try:
            if not self.motor_enable_client.service_is_ready():
                self.get_logger().warn("Motor enable service not ready")
                return

            request = SetMotorEnable.Request()
            request.enable = enable

            future = self.motor_enable_client.call_async(request)
            future.add_done_callback(
                lambda f: self._motor_enable_done(f, enable))

        except Exception as e:
            self.get_logger().error(f"Motor enable error: {e}")

    def _motor_enable_done(self, future, enable):
        """Callback for motor enable service result"""
        try:
            result = future.result()
            if result and result.success:
                self.motor_enabled = enable
                status = "ENABLED" if enable else "DISABLED"
                self.get_logger().info(f"Motors {status}")
            else:
                msg = result.message if result else "No response"
                self.get_logger().error(f"Motor enable failed: {msg}")
        except Exception as e:
            self.get_logger().error(f"Motor enable service error: {e}")

    def handle_mode_selection(self, msg):
        """Handle mode selection via D-pad (both axes and buttons)"""
        # Try D-pad as axes first (PS4/PS5 standard)
        if len(msg.axes) > max(DPAD_X, DPAD_Y):
            # D-pad UP - Normal mode
            if msg.axes[DPAD_Y] > 0.5:
                if self.mecanum_mode != MecanumMode.NORMAL:
                    self.mecanum_mode = MecanumMode.NORMAL
                    self.print_mode_info()
                    return

            # D-pad DOWN - Diagonal mode
            elif msg.axes[DPAD_Y] < -0.5:
                if self.mecanum_mode != MecanumMode.DIAGONAL:
                    self.mecanum_mode = MecanumMode.DIAGONAL
                    self.print_mode_info()
                    return

            # D-pad RIGHT - Strafe mode
            if msg.axes[DPAD_X] > 0.5:
                if self.mecanum_mode != MecanumMode.STRAFE:
                    self.mecanum_mode = MecanumMode.STRAFE
                    self.print_mode_info()
                    return

            # D-pad LEFT - Rotate mode
            elif msg.axes[DPAD_X] < -0.5:
                if self.mecanum_mode != MecanumMode.ROTATE:
                    self.mecanum_mode = MecanumMode.ROTATE
                    self.print_mode_info()
                    return

        # Try D-pad as buttons (fallback for some controllers)
        if len(msg.buttons) > max(DPAD_UP_BTN, DPAD_DOWN_BTN,
                                    DPAD_LEFT_BTN, DPAD_RIGHT_BTN):
            if self.button_pressed(DPAD_UP_BTN, msg):
                self.mecanum_mode = MecanumMode.NORMAL
                self.print_mode_info()
                return

            if self.button_pressed(DPAD_DOWN_BTN, msg):
                self.mecanum_mode = MecanumMode.DIAGONAL
                self.print_mode_info()
                return

            if self.button_pressed(DPAD_RIGHT_BTN, msg):
                self.mecanum_mode = MecanumMode.STRAFE
                self.print_mode_info()
                return

            if self.button_pressed(DPAD_LEFT_BTN, msg):
                self.mecanum_mode = MecanumMode.ROTATE
                self.print_mode_info()
                return

        # R3 button - Crab mode
        if self.button_pressed(R3_BUTTON, msg):
            self.mecanum_mode = MecanumMode.CRAB
            self.print_mode_info()

        # L3 button - Circle mode
        if self.button_pressed(L3_BUTTON, msg):
            self.mecanum_mode = MecanumMode.CIRCLE
            self.print_mode_info()

    def handle_gear_controls(self, msg):
        """Handle speed and angular gear changes"""
        # Speed gear (Triangle/X)
        if self.button_pressed(TRIANGLE_BUTTON, msg):
            if self.speed_gear < 1.0:
                self.speed_gear = min(1.0, self.speed_gear + 0.33)
                self.print_mode_info()

        if self.button_pressed(X_BUTTON, msg):
            if self.speed_gear > 0.33:
                self.speed_gear = max(0.33, self.speed_gear - 0.33)
                self.print_mode_info()

        # Angular gear (Square/Circle)
        if self.button_pressed(SQUARE_BUTTON, msg):
            if self.angular_gear < 1.0:
                self.angular_gear = min(1.0, self.angular_gear + 0.25)
                self.print_mode_info()

        if self.button_pressed(CIRCLE_BUTTON, msg):
            if self.angular_gear > 0.25:
                self.angular_gear = max(0.25, self.angular_gear - 0.25)
                self.print_mode_info()

    def compute_mecanum_velocity(self, left_x, left_y, right_x):
        """
        Compute velocity command based on current mecanum mode

        Args:
            left_x: Left stick X (strafe)
            left_y: Left stick Y (forward/back)
            right_x: Right stick X (rotation)

        Returns:
            Twist: Velocity command (vx, vy, wz)
        """
        cmd = Twist()

        if self.mecanum_mode == MecanumMode.NORMAL:
            # Free control - all axes independent
            cmd.linear.x = left_y * self.max_linear * self.speed_gear
            cmd.linear.y = left_x * self.max_linear * self.speed_gear
            cmd.angular.z = right_x * self.max_angular * self.angular_gear

        elif self.mecanum_mode == MecanumMode.STRAFE:
            # Pure sideways movement only
            cmd.linear.x = 0.0
            cmd.linear.y = left_x * self.max_linear * self.speed_gear
            cmd.angular.z = 0.0

        elif self.mecanum_mode == MecanumMode.DIAGONAL:
            # 45-degree diagonal movement
            magnitude = math.sqrt(left_x**2 + left_y**2)
            if magnitude > 0.1:
                # Calculate angle and snap to nearest 45° diagonal
                angle = math.atan2(left_y, left_x)
                # Snap to nearest 45° increment
                snapped_angle = round(angle / (math.pi/4)) * (math.pi/4)

                # atan2(left_y, left_x) maps stick-up to pi/2, so sin=forward(x), cos=strafe(y)
                cmd.linear.x = math.sin(snapped_angle) * magnitude * self.max_linear * self.speed_gear
                cmd.linear.y = math.cos(snapped_angle) * magnitude * self.max_linear * self.speed_gear
                cmd.angular.z = right_x * self.max_angular * self.angular_gear
            else:
                cmd.linear.x = 0.0
                cmd.linear.y = 0.0
                cmd.angular.z = right_x * self.max_angular * self.angular_gear

        elif self.mecanum_mode == MecanumMode.ROTATE:
            # Pure rotation in place (pivot)
            cmd.linear.x = 0.0
            cmd.linear.y = 0.0
            cmd.angular.z = right_x * self.max_angular * self.angular_gear

        elif self.mecanum_mode == MecanumMode.CRAB:
            # Crab walk: strafe + rotate simultaneously
            cmd.linear.x = 0.0
            cmd.linear.y = left_x * self.max_linear * self.speed_gear
            cmd.angular.z = right_x * self.max_angular * self.angular_gear

        elif self.mecanum_mode == MecanumMode.CIRCLE:
            # Drive in circles: forward + turn
            cmd.linear.x = left_y * self.max_linear * self.speed_gear
            cmd.linear.y = 0.0
            cmd.angular.z = left_x * self.max_angular * self.angular_gear  # Use left stick X for turn

        elif self.mecanum_mode == MecanumMode.PIVOT_STRAFE:
            # Strafe + rotate combined
            cmd.linear.x = 0.0
            cmd.linear.y = left_x * self.max_linear * self.speed_gear
            cmd.angular.z = left_y * self.max_angular * self.angular_gear

        return cmd

    def joy_callback(self, msg):
        """Process joystick input"""
        try:
            # Verify controller
            if len(msg.axes) < 6 or len(msg.buttons) < 8:
                return

            # Handle mode selection
            self.handle_mode_selection(msg)

            # Handle gear controls
            self.handle_gear_controls(msg)

            # Motor enable/disable (L1)
            if self.button_pressed(L1_BUTTON, msg):
                self.enable_motors(not self.motor_enabled)

            # Emergency stop (Share)
            if self.button_pressed(SHARE_BUTTON, msg):
                self.get_logger().warn("EMERGENCY STOP")
                self.enable_motors(False)
                stop_cmd = Twist()
                for _ in range(3):
                    self.cmd_vel_pub.publish(stop_cmd)
                return

            # Check R2 trigger for movement enable
            r2_pressed = msg.axes[R2_AXIS] < 0.0 or msg.buttons[R2_BUTTON] == 1

            if not r2_pressed or not self.motor_enabled:
                # Send stop command
                stop_cmd = Twist()
                self.cmd_vel_pub.publish(stop_cmd)
                return

            # Get stick inputs with deadzone
            left_x = self.apply_deadzone(msg.axes[LEFT_STICK_X])
            left_y = self.apply_deadzone(msg.axes[LEFT_STICK_Y])
            right_x = self.apply_deadzone(msg.axes[RIGHT_STICK_X])

            # Compute velocity based on current mode
            cmd = self.compute_mecanum_velocity(left_x, left_y, right_x)

            # Apply limits
            cmd.linear.x = max(-self.max_linear, min(self.max_linear, cmd.linear.x))
            cmd.linear.y = max(-self.max_linear, min(self.max_linear, cmd.linear.y))
            cmd.angular.z = max(-self.max_angular, min(self.max_angular, cmd.angular.z))

            # Debug output - show non-zero commands
            if abs(cmd.linear.x) > 0.01 or abs(cmd.linear.y) > 0.01 or abs(cmd.angular.z) > 0.01:
                self.get_logger().info(
                    f"[{self.mecanum_mode.name}] vx={cmd.linear.x:.2f}, "
                    f"vy={cmd.linear.y:.2f}, wz={cmd.angular.z:.2f}"
                )

            # Publish command
            self.cmd_vel_pub.publish(cmd)

        except Exception as e:
            self.get_logger().error(f"Joy callback error: {e}")
            stop_cmd = Twist()
            self.cmd_vel_pub.publish(stop_cmd)


def main(args=None):
    """Main function"""
    rclpy.init(args=args)

    try:
        node = Controller()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
