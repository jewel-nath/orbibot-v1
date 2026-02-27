# Overall robot system status
std_msgs/Header header

# Power status
float32 battery_voltage   # Battery voltage in Volts

# System resources
float32 cpu_percent       # CPU usage percentage (0-100)
float32 ram_percent       # RAM usage percentage (0-100)
float32 cpu_temp          # CPU temperature in Celsius
float32 disk_percent      # Disk usage percentage (0-100)

# System state
bool motors_enabled       # True if motors are enabled
bool emergency_stop       # True if emergency stop is active
bool hardware_ok          # True if all hardware is responding