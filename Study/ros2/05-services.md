# 05 - Services

**Request-response communication pattern**

---

## 🎯 Learning Objectives

- Understand when to use services vs topics
- Create service servers and clients
- Use ROS2 CLI tools for services

---

## 📞 What are Services?

**Services** are for request-response communication.

### Analogy: Restaurant Order

```
Customer (Client)                    Kitchen (Server)
     │                                        │
     │ "I'd like a pizza" (Request)          │
     │───────────────────────────────────────→│
     │                                        │ Makes pizza
     │ "Here's your pizza" (Response)        │
     │←───────────────────────────────────────│
     │                                        │

One-to-one communication with guaranteed response!
```

### Service vs Topic

| Feature | Topic | Service |
|---------|-------|---------|
| Pattern | Publish-Subscribe | Request-Response |
| One-to-one | ❌ Many subscribers | ✅ One server |
| Response | ❌ Fire-and-forget | ✅ Guaranteed reply |
| Use for | Continuous data | One-time actions |
| Example | Sensor streams | Enable motors |

---

## 📝 Service Definition (.srv file)

Services have a request and response format:

```
# orbibot_msgs/srv/SetMotorEnable.srv
bool enable        # Request: true to enable, false to disable
---
bool success       # Response: did it work?
string message     # Response: details
```

### Common Service Patterns

| Pattern | Request | Response |
|---------|---------|----------|
| Command | Parameters | Success/failure |
| Query | Query parameters | Data |
| Trigger | Empty | Success/failure |

---

## 🖥️ Creating a Service Server

```python
import rclpy
from rclpy.node import Node
from orbibot_msgs.srv import SetMotorEnable

class MotorService(Node):
    def __init__(self):
        super().__init__('motor_service')
        
        # Create service
        self.srv = self.create_service(
            SetMotorEnable,           # Service type
            '/orbibot/set_motor_enable',  # Service name
            self.enable_callback      # Handler function
        )
        
        self.motors_enabled = False
    
    def enable_callback(self, request, response):
        # request.enable = True or False
        
        if request.enable:
            self.motors_enabled = True
            response.success = True
            response.message = "Motors enabled"
            self.get_logger().info("Motors enabled")
        else:
            self.motors_enabled = False
            response.success = True
            response.message = "Motors disabled"
            self.get_logger().info("Motors disabled")
        
        return response  # Must return the response!

def main(args=None):
    rclpy.init(args=args)
    node = MotorService()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### Key Points

```python
def callback(self, request, response):
    # Access request data
    enable = request.enable
    
    # Set response data
    response.success = True
    response.message = "OK"
    
    # MUST return response
    return response
```

---

## 📞 Creating a Service Client

```python
import rclpy
from rclpy.node import Node
from orbibot_msgs.srv import SetMotorEnable

class MotorClient(Node):
    def __init__(self):
        super().__init__('motor_client')
        
        # Create client
        self.client = self.create_client(
            SetMotorEnable,
            '/orbibot/set_motor_enable'
        )
        
        # Wait for service to be available
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Service not available, waiting...')
    
    def send_request(self, enable):
        # Create request
        request = SetMotorEnable.Request()
        request.enable = enable
        
        # Call service (asynchronous)
        self.future = self.client.call_async(request)
        
        # Wait for response
        rclpy.spin_until_future_complete(self, self.future)
        
        # Get result
        response = self.future.result()
        return response

def main(args=None):
    rclpy.init(args=args)
    client = MotorClient()
    
    # Enable motors
    response = client.send_request(True)
    print(f"Success: {response.success}, Message: {response.message}")
    
    client.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### Async vs Sync

```python
# Async (non-blocking) - preferred
self.future = self.client.call_async(request)
# Do other work...
response = self.future.result()

# Sync (blocking) - simpler but blocks node
response = self.client.call(request)
```

---

## 🖥️ CLI Tools for Services

### List Services

```bash
# All services
ros2 service list

# With types
ros2 service list -t

# Filter
ros2 service list | grep orbibot
```

### Call a Service

```bash
# Basic call
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"

# With response
# success: true
# message: "Motors enabled"

# Disable motors
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: false}"
```

### Service Info

```bash
# Type
ros2 service type /orbibot/set_motor_enable
# Result: orbibot_msgs/srv/SetMotorEnable

# Show interface
ros2 interface show orbibot_msgs/srv/SetMotorEnable
```

---

## 🔄 Complete Example: OrbiBot Hardware Services

### Service 1: Enable Motors

```python
# Server (in hardware_node.py)
def enable_callback(self, request, response):
    with self._state_lock:
        if request.enable and not self.emergency_stop:
            self.motors_enabled = True
            response.success = True
            response.message = "Motors enabled"
        elif not request.enable:
            self.bot.set_car_motion(0, 0, 0)  # Stop first!
            self.motors_enabled = False
            response.success = True
            response.message = "Motors disabled"
        else:
            response.success = False
            response.message = "Emergency stop active"
    return response
```

### Service 2: Reset Odometry

```bash
# Call from CLI
ros2 service call /orbibot/reset_odometry orbibot_msgs/srv/ResetOdometry "{}"
```

```python
# Server callback
def reset_callback(self, request, response):
    try:
        self.bot.reset_odometry()
        self._accumulated_distance = 0.0
        response.success = True
        response.message = "Odometry reset"
    except Exception as e:
        response.success = False
        response.message = str(e)
    return response
```

---

## 🎯 When to Use What?

### Use Topics When:

```
✅ Continuous data stream (sensors)
✅ Multiple subscribers needed
✅ Fire-and-forget is OK
✅ High frequency (50Hz+)
```

### Use Services When:

```
✅ One-time action (enable/disable)
✅ Need confirmation (did it work?)
✅ Configuration changes
✅ Infrequent operations
```

---

## 🧪 Exercise: Create a Battery Query Service

### Task

Create a service that returns current battery voltage.

**Service definition:**
```
# GetBattery.srv
---
float32 voltage
bool low_battery  # True if < 11.0V
```

**Steps:**
1. Create .srv file
2. Build to generate Python code
3. Create server node
4. Create client node (or use CLI)

---

## 🎯 Key Takeaways

1. **Services** = Request-response (one-to-one)
2. **Topics** = Continuous broadcast (many-to-many)
3. Services have **request** and **response** parts
4. Servers **must return** the response object
5. Clients can call **async** or **sync**

---

## 📖 Next Steps

Learn about actions for long-running tasks:

**→ Continue to:** [06-actions.md](06-actions.md)

Or learn about parameters:

**→ Or go to:** [07-parameters.md](07-parameters.md)

---

*Last Updated: March 2026*