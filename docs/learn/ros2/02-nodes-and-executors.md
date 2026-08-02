---
title: "02 - Nodes and Executors"
type: learn
area: ros2
tags:
  - learn
  - ros2
---

# 02 - Nodes and Executors

**The building blocks of ROS2 programs**

---

## 🎯 Learning Objectives

- Understand what a node is
- Create a basic ROS2 node
- Know how executors work
- Use node lifecycle

---

## 🤖 What is a Node?

A **node** is a single-purpose program in ROS2.

### Analogy: Restaurant Staff

```
Restaurant (Robot System)
├── Chef Node       → Cooks food
├── Waiter Node     → Takes orders
├── Cashier Node    → Handles payments
└── Manager Node    → Monitors everything

Each node does ONE thing, but they work together!
```

### ROS2 Node Characteristics

| Property | Description |
|----------|-------------|
| **Name** | Unique identifier (e.g., `hardware_node`) |
| **Purpose** | Single responsibility |
| **Communication** | Topics, services, actions |
| **Lifecycle** | Init → Spin → Shutdown |

---

## 📝 Minimal Node Example

```python
import rclpy
from rclpy.node import Node

class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')  # Node name
        self.get_logger().info('Hello from my_node!')

def main(args=None):
    rclpy.init(args=args)           # Initialize ROS2
    node = MyNode()                  # Create node
    rclpy.spin(node)                 # Keep node running
    node.destroy_node()              # Cleanup
    rclpy.shutdown()                 # Shutdown ROS2

if __name__ == '__main__':
    main()
```

### Key Parts

```python
rclpy.init()        # One per program - starts ROS2
Node.__init__()     # Creates node, registers with ROS2
rclpy.spin()        # Enters event loop - processes callbacks
rclpy.shutdown()    # Cleanup when done
```

---

## ⏱️ Adding a Timer

Nodes do work using timers:

```python
class TimerNode(Node):
    def __init__(self):
        super().__init__('timer_node')
        
        # Create timer: 1.0 second period
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.count = 0
    
    def timer_callback(self):
        self.count += 1
        self.get_logger().info(f'Count: {self.count}')

# This runs every 1 second!
```

### Timer Frequencies

| Period (s) | Frequency (Hz) | Use Case |
|------------|----------------|----------|
| 0.02 | 50 | Fast sensors |
| 0.1 | 10 | Status updates |
| 1.0 | 1 | Slow monitoring |

---

## 🔄 Executors

An **executor** manages node's callbacks.

### Single-Threaded (Default)

```python
node = MyNode()
rclpy.spin(node)  # Uses default executor
```

- Processes callbacks one at a time
- Simple, predictable

### Multi-Threaded

```python
from rclpy.executors import MultiThreadedExecutor

def main(args=None):
    rclpy.init(args=args)
    node = MyNode()
    
    # Multi-threaded executor
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    executor.spin()
    
    node.destroy_node()
    rclpy.shutdown()
```

- Processes callbacks in parallel
- Better for CPU-intensive work
- Used in `orbibot_hardware`!

---

## 🎯 Node Best Practices

### DO:

```python
✅ Keep callbacks fast (<10ms)
✅ Use descriptive node names
✅ Proper shutdown cleanup
✅ One node per logical component
```

### DON'T:

```python
❌ Block in callbacks (use threads if needed)
❌ Create too many nodes (overhead)
❌ Forget to call destroy_node()
```

---

## 🎯 Key Takeaways

1. **Node** = Single-purpose ROS2 program
2. **Timer** = Periodic execution
3. **Executor** = Manages callbacks
4. **spin()** = Keeps node alive and processing

---

## 📖 Next Steps

Learn about topics:

**→ Continue to:** [[03-topics-pub-sub]]

---

*Last Updated: March 2026*