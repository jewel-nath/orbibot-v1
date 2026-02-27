# Safety system status
std_msgs/Header header

# Emergency states
bool emergency_stop       # Emergency stop button pressed
bool cmd_timeout          # Command timeout detected
bool low_battery          # Battery voltage too low
bool hardware_fault       # Hardware communication fault

# Safety limits
bool velocity_limit       # Velocity command exceeded limits
bool temperature_limit    # Temperature too high

# Safety actions taken
bool motors_disabled      # Motors automatically disabled
uint32 fault_code         # Specific fault code for diagnostics