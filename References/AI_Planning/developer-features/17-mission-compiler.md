# 17. Natural Language Mission Compiler

**Difficulty:** Hard
**Category:** Autonomy & Planning
**Why it's unique:** Compiles English to executable behavior trees
**Prerequisites:** Features #9 (semantic navigation), #16 (conversational interface)

## Description

Go beyond simple "go to kitchen" commands - support complex, conditional missions with loops, conditions, and error handling.

## Example Mission Specifications

**Mission 1: Morning Routine**
```
Every morning at 8am, check all rooms. If you find a person, greet them
and ask if they need coffee. Remember their preferences. If a window is
open and it's raining outside, close it and notify me.
```

**Mission 2: Security Patrol with Anomaly Detection**
```
Patrol between the living room, kitchen, and front door every 30 minutes.
At each location, take a photo and compare it with the baseline. If you
detect motion or a new object, approach carefully and send me an alert with
the image. If battery drops below 25%, return to charger.
```

**Mission 3: Fetch and Deliver**
```
Go to the kitchen, find the red coffee mug (it's usually on the counter or
in the cabinet), bring it to me in the office, then return to idle mode.
If you can't find it after 2 minutes, ask me where it is.
```

## Implementation: Mission Compiler

```python
#!/usr/bin/env python3
"""
Natural Language Mission Compiler
Converts natural language to executable behavior trees
"""

import anthropic
from lxml import etree
import yaml

class MissionCompiler:
    def __init__(self):
        self.claude = anthropic.Anthropic()

        # Available behavior tree nodes
        self.available_actions = self.load_action_catalog()

    def compile_mission(self, natural_language: str) -> dict:
        """Compile natural language mission to behavior tree."""

        prompt = f"""
        Convert the following mission description into a BehaviorTree XML format.

        **Mission:**
        {natural_language}

        **Available Actions:**
        {yaml.dump(self.available_actions, default_flow_style=False)}

        **Requirements:**
        1. Use standard BehaviorTree.CPP XML format
        2. Include proper error handling (Fallback nodes)
        3. Use BlackBoard variables for state sharing
        4. Add descriptive names to all nodes
        5. Include timeout parameters where appropriate

        **Example structure:**
        ```xml
        <BehaviorTree ID="mission_name">
          <Sequence>
            <Action ID="navigate_to" room="kitchen"/>
            <Fallback>
              <Condition ID="person_detected"/>
              <Sequence>
                <Action ID="greet_person"/>
                <Action ID="ask_question" text="Would you like coffee?"/>
              </Sequence>
            </Fallback>
          </Sequence>
        </BehaviorTree>
        ```

        Output the complete XML behavior tree.
        """

        response = self.claude.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Extract XML from response
        xml_str = self.extract_xml(response.content[0].text)

        # Validate XML
        tree = etree.fromstring(xml_str.encode('utf-8'))

        # Generate Python execution wrapper
        executor_code = self.generate_executor(tree)

        return {
            'xml': xml_str,
            'tree': tree,
            'executor_code': executor_code,
            'estimated_duration': self.estimate_duration(tree)
        }

    def load_action_catalog(self) -> dict:
        """Load available behavior tree action nodes."""
        return {
            'navigation': {
                'navigate_to': {
                    'params': ['room: string', 'x: float', 'y: float'],
                    'description': 'Navigate to location'
                },
                'approach_object': {
                    'params': ['object: string', 'distance: float'],
                    'description': 'Approach detected object'
                },
                'return_home': {
                    'params': [],
                    'description': 'Return to home position'
                }
            },
            'perception': {
                'detect_person': {
                    'params': [],
                    'returns': 'bool',
                    'description': 'Check if person in view'
                },
                'detect_object': {
                    'params': ['class: string'],
                    'returns': 'bool',
                    'description': 'Check if specific object detected'
                },
                'compare_with_baseline': {
                    'params': ['location: string'],
                    'returns': 'bool',
                    'description': 'Check for scene changes'
                }
            },
            'interaction': {
                'greet_person': {
                    'params': ['name: optional[string]'],
                    'description': 'Greet detected person'
                },
                'ask_question': {
                    'params': ['text: string'],
                    'returns': 'string',
                    'description': 'Ask question and wait for answer'
                },
                'notify_user': {
                    'params': ['message: string', 'severity: string'],
                    'description': 'Send notification to user'
                }
            },
            'manipulation': {
                'pick_object': {
                    'params': ['object: string'],
                    'description': 'Pick up object (requires arm)'
                },
                'place_object': {
                    'params': ['location: string'],
                    'description': 'Place held object'
                }
            },
            'system': {
                'wait': {
                    'params': ['duration: float'],
                    'description': 'Wait for duration (seconds)'
                },
                'set_blackboard': {
                    'params': ['key: string', 'value: any'],
                    'description': 'Store value in blackboard'
                },
                'check_battery': {
                    'params': ['threshold: float'],
                    'returns': 'bool',
                    'description': 'Check if battery above threshold'
                }
            }
        }

    def generate_executor(self, tree: etree.Element) -> str:
        """Generate Python code to execute the behavior tree."""

        code = f"""
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import py_trees
import py_trees_ros

class MissionExecutor(Node):
    def __init__(self):
        super().__init__('mission_executor')

        # Load behavior tree
        self.tree = self.create_behavior_tree()

        # Setup tree update timer
        self.tree_timer = self.create_timer(0.1, self.tick_tree)  # 10 Hz

        self.get_logger().info('Mission executor started')

    def create_behavior_tree(self):
        # Generated from compiled mission
        # (Code would be generated based on XML structure)
        pass

    def tick_tree(self):
        self.tree.tick()

def main():
    rclpy.init()
    executor = MissionExecutor()
    rclpy.spin(executor)
    executor.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
        """

        return code

    def extract_xml(self, text: str) -> str:
        """Extract XML from Claude's response."""
        if '```xml' in text:
            return text.split('```xml')[1].split('```')[0].strip()
        elif '<BehaviorTree' in text:
            start = text.index('<BehaviorTree')
            end = text.rindex('</BehaviorTree>') + len('</BehaviorTree>')
            return text[start:end]
        else:
            raise ValueError("No valid XML found in response")

# Example usage
compiler = MissionCompiler()

mission = """
Every 30 minutes, patrol the house. At each room, check for people.
If found, greet them. If battery below 25%, go charge.
"""

result = compiler.compile_mission(mission)
print(result['xml'])
```

## Benefits

1. **No Programming Required**: Non-technical users can create missions
2. **Complex Logic**: Supports conditionals, loops, error handling
3. **Maintainable**: Natural language is easier to understand than code
4. **Rapid Prototyping**: Test mission ideas in minutes
5. **Version Control Friendly**: Missions are readable text

---

[← Previous: Conversational Interface](16-conversational-interface.md) | [↑ Index](README.md) | [Next: Multi-Agent Architecture →](18-multi-agent-architecture.md)
