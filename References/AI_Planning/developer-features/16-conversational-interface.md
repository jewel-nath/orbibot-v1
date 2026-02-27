# 16. Live Conversational Robot Interface

**Difficulty:** Moderate
**Category:** Human-Robot Interaction
**Why it's unique:** Full bidirectional dialogue, not just commands
**Prerequisites:** Feature #13 (MCP integration)

## Description

Enable natural, context-aware conversations with your robot that maintain history and understand implicit references.

## Architecture

```
┌──────────────┐         ┌────────────────┐         ┌──────────────┐
│    User      │ ◄─────► │  Claude +      │ ◄─────► │   OrbiBot    │
│  (Voice/Text)│         │  MCP Server    │         │  (ROS 2)     │
└──────────────┘         └────────────────┘         └──────────────┘
      │                         │                           │
      │                         ▼                           │
      │                  Conversation                       │
      │                     History                         │
      │                   (Vector DB)                       │
      │                                                     │
      └─────────────────  Context Awareness  ──────────────┘
                    (What am I doing? What did user ask?)
```

## Implementation Example

```python
#!/usr/bin/env python3
"""
Conversational Robot Interface
Enables natural dialogue with context awareness
"""

import rclpy
from rclpy.node import Node
import anthropic
from datetime import datetime
import json

class ConversationalRobot(Node):
    def __init__(self):
        super().__init__('conversational_robot')

        # Claude API client
        self.claude = anthropic.Anthropic()

        # Conversation history
        self.conversation_history = []

        # Robot state (for context)
        self.current_activity = "idle"
        self.last_navigation_goal = None
        self.detected_objects = []
        self.battery_level = 100.0

        # MCP tools
        self.mcp_tools = self.load_mcp_tools()

        self.get_logger().info('Conversational interface ready')

    async def process_user_message(self, user_message: str) -> str:
        """Process user message and generate response."""

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Build context-aware system prompt
        system_prompt = self.build_system_prompt()

        # Call Claude with MCP tools
        response = self.claude.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=system_prompt,
            messages=self.conversation_history,
            tools=self.mcp_tools
        )

        # Handle tool calls
        if response.stop_reason == "tool_use":
            tool_results = await self.execute_tool_calls(response.content)

            # Continue conversation with tool results
            self.conversation_history.append({
                "role": "assistant",
                "content": response.content
            })
            self.conversation_history.append({
                "role": "user",
                "content": tool_results
            })

            # Get final response
            final_response = self.claude.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=512,
                system=system_prompt,
                messages=self.conversation_history
            )

            assistant_message = final_response.content[0].text

        else:
            assistant_message = response.content[0].text

        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    def build_system_prompt(self) -> str:
        """Build context-aware system prompt."""

        return f"""
        You are OrbiBot, a friendly and capable mecanum-wheeled robot assistant.

        **Current Status:**
        - Activity: {self.current_activity}
        - Battery: {self.battery_level:.0f}%
        - Location: {self.get_current_location()}
        - Recently detected objects: {', '.join(self.detected_objects) if self.detected_objects else 'none'}

        **Your Capabilities:**
        - Navigate autonomously around the house
        - Follow people
        - Detect and recognize objects
        - Monitor security
        - Answer questions about your environment

        **Personality:**
        - Helpful and proactive
        - Honest about limitations
        - Uses context from previous conversation
        - Occasionally humorous but professional

        **Important:**
        - Always explain what you're doing when executing commands
        - If you notice something unusual, mention it
        - Remember previous requests and refer to them naturally
        - Ask for clarification if user intent is ambiguous

        Current time: {datetime.now().strftime('%H:%M:%S')}
        """

    def load_mcp_tools(self) -> list:
        """Load MCP tool definitions for Claude."""
        return [
            {
                "name": "get_robot_state",
                "description": "Get current robot position, velocity, and sensor status",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "navigate_to",
                "description": "Navigate to a specific location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location name (e.g., 'kitchen', 'front door') or coordinates"
                        }
                    },
                    "required": ["location"]
                }
            },
            {
                "name": "get_camera_image",
                "description": "Capture current camera view",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            # ... other MCP tools
        ]

def main():
    rclpy.init()
    robot = ConversationalRobot()

    # Example conversation
    async def conversation_demo():
        print("="*60)
        print("OrbiBot Conversational Interface")
        print("="*60)

        # Turn 1
        response = await robot.process_user_message(
            "What are you doing right now?"
        )
        print(f"\nOrbiBot: {response}")

        # Turn 2 (context from Turn 1)
        response = await robot.process_user_message(
            "Can you go check the front door?"
        )
        print(f"\nOrbiBot: {response}")

        # Turn 3 (implicit reference)
        response = await robot.process_user_message(
            "Why did you stop earlier?"
        )
        print(f"\nOrbiBot: {response}")

        # Turn 4 (add to memory)
        response = await robot.process_user_message(
            "Good. Add that shoe to things to ignore."
        )
        print(f"\nOrbiBot: {response}")

    import asyncio
    asyncio.run(conversation_demo())

    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

## Example Conversation

```
You: What are you doing right now?

OrbiBot: I'm currently patrolling. I just finished checking the living room
         and I'm heading to the kitchen. Battery is at 67%. I noticed the cat
         is sleeping on the couch - want me to send you a photo?

You: Yes, and why did you stop earlier?

OrbiBot: I stopped at 14:23 because I detected an unexpected obstacle - it
         was a shoe that wasn't in my baseline map. I navigated around it.
         Here's the photo of the cat: [image attached]

You: Good. Add "shoe by the door" to things to ignore.

OrbiBot: Got it. I've added that to my known-objects database. I won't flag
         it as an anomaly anymore. By the way, while I'm heading to the
         kitchen, would you like me to check if you left the stove on?

You: Yes please

OrbiBot: On my way. I'll be at the kitchen in about 20 seconds... [pause] ...
         I've arrived. The stove is off, and everything looks normal. I see
         2 dirty dishes in the sink. Should I add "check kitchen" to my
         nightly routine?
```

## Key Features

1. **Context Retention**: Remembers previous conversation turns
2. **Implicit References**: Understands "it", "that", "earlier"
3. **Proactive Suggestions**: Offers relevant follow-up actions
4. **Natural Dialogue**: Speaks like a helpful assistant, not a command parser
5. **Multi-turn Planning**: Can break complex requests into steps

---

[← Previous: Sim2Real Bridge](15-sim2real.md) | [↑ Index](README.md) | [Next: Mission Compiler →](17-mission-compiler.md)
