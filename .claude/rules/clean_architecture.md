---
description: Clean Architecture Reference (aspirational, for future refactoring)
---

# Clean Architecture Reference

**Note**: OrbiBot follows standard ROS 2 package-level separation. This is an aspirational reference for future complex packages (e.g., `orbibot_ai`).

## Principle: Separate Concerns by Layer

```
Domain Layer      → Pure business logic, no ROS 2 dependencies
Application Layer → Use cases, orchestrates domain logic
Infrastructure    → ROS 2 nodes, publishers, subscribers (adapters)
```

## When to Apply (Future)

- Complex nodes with significant business logic (AI, planning)
- Nodes that need unit testing without ROS 2 runtime
- Code that might be reused outside ROS 2

## When NOT to Apply

- Standard sensor/actuator nodes (hardware_node)
- Launch/config packages (bringup, navigation)
- Simple pub/sub nodes (obstacle_detector, teleop)

## Key Rule

Domain code must NOT import `rclpy`, `geometry_msgs`, or any ROS 2 package. Keep business logic in pure Python/C++ classes. ROS 2 nodes wrap these classes as adapters.

```python
# GOOD: Domain logic is pure Python
class FrontierSelector:
    def select_best(self, frontiers, robot_position):
        # Pure logic, no ROS dependencies
        return min(frontiers, key=lambda f: f.distance_to(robot_position))

# GOOD: ROS node wraps domain logic
class FrontierExplorerNode(Node):
    def __init__(self):
        super().__init__('frontier_explorer')
        self._selector = FrontierSelector()  # Domain injected
```
