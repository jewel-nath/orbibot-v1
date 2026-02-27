# 18. Agentic Robot Controller (Multi-Agent Architecture)

**Difficulty:** Hard
**Category:** Advanced Autonomy
**Why it's unique:** True agentic autonomy with specialized sub-agents
**Prerequisites:** Features #13, #14, #16 (MCP, debugging, conversation)

## Description

Implement a multi-agent system where specialized agents handle different aspects of robot operation, coordinated by an orchestrator.

## Architecture

```
                    ┌─────────────────────────────┐
                    │     Orchestrator Agent      │
                    │   (Claude - High-level)     │
                    └─────────────┬───────────────┘
                                  │
        ┌─────────────┬───────────┼───────────┬─────────────┐
        ▼             ▼           ▼           ▼             ▼
   ┌─────────┐  ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐
   │Perception│  │ Planning │ │Execution│ │ Safety  │ │ Memory    │
   │  Agent   │  │  Agent   │ │  Agent  │ │  Agent  │ │  Agent    │
   └─────────┘  └──────────┘ └─────────┘ └─────────┘ └───────────┘
       │             │            │           │            │
   YOLO/VLM     Nav2 goals    cmd_vel    E-stop      Vector DB
   Depth proc   Path plan     PID ctrl   Collision   Episode log
```

## Agent Responsibilities

| Agent | Role | Responsibilities |
|-------|------|------------------|
| **Orchestrator** | Coordination | Decomposes high-level goals, delegates to specialists, resolves conflicts |
| **Perception** | Sensing | Processes camera/lidar, maintains object database, identifies anomalies |
| **Planning** | Strategy | Generates navigation plans, handles replanning, optimizes paths |
| **Execution** | Control | Low-level motor control, trajectory following, mecanum kinematics |
| **Safety** | Monitoring | Watches for collisions, monitors battery, overrides if needed |
| **Memory** | Learning | Stores successful strategies, learns from failures, recalls similar situations |

## Implementation: Multi-Agent System

```python
#!/usr/bin/env python3
"""
Agentic Robot Controller
Multi-agent system with specialized sub-agents
"""

import rclpy
from rclpy.node import Node
import anthropic
from typing import Dict, List
import json

class OrchestratorAgent:
    """High-level agent that coordinates specialist agents."""

    def __init__(self, ros_node: Node):
        self.node = ros_node
        self.claude = anthropic.Anthropic()

        # Initialize specialist agents
        self.agents = {
            'perception': PerceptionAgent(ros_node),
            'planning': PlanningAgent(ros_node),
            'execution': ExecutionAgent(ros_node),
            'safety': SafetyAgent(ros_node),
            'memory': MemoryAgent(ros_node)
        }

        self.active_mission = None

    async def process_command(self, user_command: str):
        """Process high-level user command."""

        # Decompose command into sub-tasks
        task_plan = await self.decompose_command(user_command)

        # Execute task plan
        for task in task_plan['tasks']:
            await self.execute_task(task)

    async def decompose_command(self, command: str) -> dict:
        """Use Claude to decompose command into agent tasks."""

        # Get current context from all agents
        context = await self.gather_agent_context()

        prompt = f"""
        **User Command:** {command}

        **Current Robot State:**
        {json.dumps(context, indent=2)}

        **Available Agents:**
        - perception: Object detection, scene understanding
        - planning: Navigation path generation
        - execution: Motor control, trajectory following
        - safety: Collision avoidance, battery monitoring
        - memory: Recall past experiences, learn patterns

        Decompose this command into a sequence of agent tasks.
        Format as JSON with: agent, action, parameters, success_criteria

        Example:
        {{
          "mission_summary": "Patrol the house and report anomalies",
          "tasks": [
            {{"agent": "planning", "action": "generate_patrol_route",
              "params": {{"rooms": ["living_room", "kitchen", "bedroom"]}}}},
            {{"agent": "execution", "action": "follow_path",
              "params": {{"path": "{{patrol_route}}"}}}},
            {{"agent": "perception", "action": "compare_scenes",
              "params": {{"frequency_hz": 1.0}}}}
          ]
        }}
        """

        response = self.claude.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        task_plan = json.loads(response.content[0].text)
        return task_plan

    async def execute_task(self, task: dict):
        """Delegate task to appropriate agent."""
        agent_name = task['agent']
        action = task['action']
        params = task.get('params', {})

        agent = self.agents[agent_name]
        result = await agent.execute_action(action, params)

        # Check success
        if not result['success']:
            await self.handle_task_failure(task, result)

        return result

    async def gather_agent_context(self) -> dict:
        """Collect current state from all agents."""
        context = {}
        for name, agent in self.agents.items():
            context[name] = await agent.get_state()
        return context

    async def handle_task_failure(self, task: dict, result: dict):
        """Handle task failure with retry or replan."""
        self.node.get_logger().warn(f"Task failed: {task['action']}")

        # Ask Claude for recovery strategy
        recovery = await self.get_recovery_strategy(task, result)

        if recovery['action'] == 'retry':
            await self.execute_task(task)
        elif recovery['action'] == 'replan':
            # Generate alternative plan
            pass
        elif recovery['action'] == 'abort':
            self.node.get_logger().error("Mission aborted")


class PerceptionAgent:
    """Handles all sensing and perception tasks."""

    def __init__(self, ros_node: Node):
        self.node = ros_node
        self.detected_objects = []
        self.scene_baseline = {}

    async def execute_action(self, action: str, params: dict) -> dict:
        if action == "detect_objects":
            return await self.detect_objects(params)
        elif action == "compare_scenes":
            return await self.compare_scenes(params)
        # ... other actions

    async def detect_objects(self, params: dict) -> dict:
        # Run YOLO detection
        # Update object database
        pass

    async def get_state(self) -> dict:
        return {
            "detected_objects": self.detected_objects,
            "camera_active": True,
            "lidar_active": True
        }


class PlanningAgent:
    """Handles path planning and mission planning."""

    def __init__(self, ros_node: Node):
        self.node = ros_node
        self.current_plan = None

    async def execute_action(self, action: str, params: dict) -> dict:
        if action == "generate_patrol_route":
            return await self.generate_patrol_route(params)
        elif action == "replan_path":
            return await self.replan_path(params)

    async def generate_patrol_route(self, params: dict) -> dict:
        rooms = params['rooms']
        # Generate optimal patrol route through rooms
        # Use Nav2 to get paths between waypoints
        pass


class ExecutionAgent:
    """Handles low-level control execution."""

    def __init__(self, ros_node: Node):
        self.node = ros_node

    async def execute_action(self, action: str, params: dict) -> dict:
        if action == "follow_path":
            return await self.follow_path(params)
        elif action == "move_velocity":
            return await self.move_velocity(params)


class SafetyAgent:
    """Monitors safety and can override other agents."""

    def __init__(self, ros_node: Node):
        self.node = ros_node
        self.estop_triggered = False

        # Monitor safety continuously
        self.node.create_timer(0.1, self.safety_check)

    def safety_check(self):
        # Check battery
        # Check for imminent collisions
        # Check for stuck condition

        if self.detect_danger():
            self.trigger_estop()

    def trigger_estop(self):
        self.node.get_logger().error("EMERGENCY STOP TRIGGERED")
        # Publish zero velocity
        # Notify orchestrator


class MemoryAgent:
    """Stores and recalls past experiences."""

    def __init__(self, ros_node: Node):
        self.node = ros_node
        self.episode_database = []

    async def store_episode(self, episode: dict):
        """Store successful or failed episode for learning."""
        self.episode_database.append(episode)

    async def recall_similar(self, situation: dict) -> List[dict]:
        """Find similar past situations."""
        # Use vector similarity search
        pass


def main():
    rclpy.init()
    node = Node('agentic_controller')

    orchestrator = OrchestratorAgent(node)

    # Example command
    user_command = """
    Patrol the house every hour, report anything unusual,
    and if battery drops below 30%, go charge yourself
    """

    import asyncio
    asyncio.run(orchestrator.process_command(user_command))

    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

## Benefits of Multi-Agent Architecture

1. **Modularity**: Each agent is independent and testable
2. **Specialization**: Agents optimized for specific tasks
3. **Fault Tolerance**: Failure in one agent doesn't crash system
4. **Scalability**: Easy to add new specialist agents
5. **Explainability**: Agent decisions can be logged and understood

---

[← Previous: Mission Compiler](17-mission-compiler.md) | [↑ Index](README.md) | [Implementation Roadmap →](roadmap.md)
