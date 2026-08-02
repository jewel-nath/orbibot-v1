# Coding Standards

**⚠️ MANDATORY — MUST READ BEFORE WRITING ANY CODE**

These naming conventions are REQUIRED for all new code and modifications.
Violating these conventions is NOT acceptable.

## Python Naming (PEP 8 Compliant)

**Classes** — `PascalCase` (no underscores between words)
- ✅ `OrbiBotControlManager`, `RosmasterDriver`, `HardwareNode`
- ❌ `OrbiBot_Control_Manager`, `Rosmaster_Driver`

**Functions and Methods** — `snake_case`
- ✅ `calculate_odometry()`, `publish_tf_transform()`, `encoder_callback()`
- Private methods: prefix with single underscore `_method_name()`

**Variables** — `snake_case`
- Instance: `self.odom_x`, `self.prev_encoders`
- Private instance: `self._battery_voltage`, `self._data_lock`

**Constants** — `UPPER_SNAKE_CASE` at **module level** (after imports, before class definitions)
```python
ENCODER_PPR = 1320
INT32_MAX = 2147483647
MAX_VELOCITY = 2.0
```
- ❌ Do NOT use class-level constants like `self.ENCODER_PPR`

**Private Members** — `_single_underscore` prefix
- ❌ Avoid `__double_underscore` (name mangling) unless truly needed for inheritance
- Magic methods (`__init__`, `__del__`) keep double underscores — that's correct

**Docstrings** — Google style with `Args:`, `Returns:`, `Raises:` where applicable
```python
def encoder_callback(self, msg: Int32MultiArray) -> None:
    """
    Process raw encoder counts and calculate odometry.

    Applies mecanum forward kinematics to convert wheel displacements
    into robot motion in the odom frame.

    Args:
        msg: Encoder counts [FL, BL, FR, BR] in ticks
    """
```

## C Naming (Firmware)

**Functions** — `module_action` (snake_case with module prefix)
- ✅ `mecanum_inverse_kinematics()`, `pid_update()`, `encoder_get_count()`

**Variables** — `snake_case`
- ✅ `wheel_velocity`, `encoder_count`, `battery_voltage`

**Structs and Typedefs** — `snake_case_t` (with `_t` suffix)
- ✅ `robot_velocity_t`, `wheel_velocity_t`, `pid_controller_t`

**Constants and Macros** — `UPPER_SNAKE_CASE`
- ✅ `ENCODER_PPR`, `MAX_PWM_VALUE`, `WHEELBASE_M`

## File and Directory Naming

| Type | Format | Examples |
|------|--------|---------|
| Python files | `snake_case.py` | `control_manager.py`, `hardware_node.py` |
| C/H files | `snake_case.c/.h` | `mecanum_kinematics.c`, `pid_controller.h` |
| ROS 2 packages | `snake_case` | `orbibot_control`, `orbibot_hardware` |
| Config files | `snake_case.yaml` | `hardware_params.yaml`, `nav2_params.yaml` |
| Launch files | `snake_case.launch.py` | `system.launch.py`, `navigation.launch.py` |
| Docs | `kebab-case.md` | `firmware-architecture.md`, `mecanum-guide.md` |
| Exception | `README.md` | Universal convention — keep uppercase |

## Comment Guidelines

**When to comment:**
- Complex algorithms (kinematics, PID, coordinate transforms)
- Non-obvious logic (wraparound handling, edge cases)
- Hardware-specific behavior (encoder directions, IMU frames)
- Coordinate frame conventions

**When NOT to comment:**
- Obvious, self-explanatory code
- Redundant statements that just repeat the code

**Style:**
- Capitalize the first word of inline comments
- Use complete sentences for multi-line explanations
- Document coordinate frames explicitly:
  ```python
  # ROS frame: X=forward, Y=left, Z=up (CCW rotation positive)
  dx_robot = (d_fl + d_bl + d_fr + d_br) / 4.0
  ```

## Quick-Reference Examples

**Good Python:**
```python
# Module-level constants
ENCODER_PPR = 1320
MAX_VELOCITY = 2.0

class OrbiBotControlManager(Node):
    """Control manager for encoder-based odometry."""

    def __init__(self):
        super().__init__('orbibot_control_manager')
        self._battery_voltage = 0.0  # Private
        self.wheel_radius = 0.05     # Public parameter

    def _parse_data(self, data: bytes) -> dict:
        """Parse incoming serial data (private method)."""
        pass

    def publish_odometry(self, current_time):
        """Publish odometry message and TF transform."""
        pass
```

**Good C:**
```c
#define ENCODER_PPR   1320
#define MAX_PWM_VALUE 4095

typedef struct {
    float vx;
    float vy;
    float omega;
} robot_velocity_t;

void mecanum_inverse_kinematics(const robot_velocity_t *robot,
                                 wheel_velocity_t *wheels) {
    wheels->fl = robot->vx - robot->vy - WHEELBASE_PLUS_TRACK * robot->omega;
}
```
