# Motor encoder feedback and status
std_msgs/Header header

# Raw encoder counts for each motor (4 motors)
int32[] encoder_counts     # Raw encoder counts since startup

# Calculated positions and velocities 
float64[] positions        # Joint positions in radians
float64[] velocities       # Joint velocities in rad/s

# Motor status
bool[] motor_enabled       # Per-motor enable status
float32[] motor_currents   # Motor currents in Amps (if available)