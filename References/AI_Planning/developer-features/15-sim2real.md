# 15. Robot Simulation-to-Real Bridge with Claude

**Difficulty:** Moderate/Hard
**Category:** Validation & Calibration
**Why it's unique:** AI-assisted sim2real transfer
**Prerequisites:** Feature #14 (debugging agent), Gazebo setup

## Description

Use Claude to analyze discrepancies between Gazebo simulation and real robot, automatically suggesting calibration improvements.

## Implementation

```python
#!/usr/bin/env python3
"""
Sim2Real Analysis Agent
Compares simulation vs real-world performance and suggests calibration fixes
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry, Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import euclidean
import json

class Sim2RealAgent(Node):
    def __init__(self):
        super().__init__('sim2real_agent')

        # Data collection
        self.sim_data = {'odom': [], 'cmd_vel': [], 'time': []}
        self.real_data = {'odom': [], 'cmd_vel': [], 'time': []}

        self.mode = None  # 'sim' or 'real'

    async def run_comparison_mission(self, mission: dict):
        """Run the same mission in sim and on real robot."""

        # 1. Run in simulation
        self.mode = 'sim'
        sim_result = await self.execute_mission(mission, sim=True)

        # 2. Run on real robot
        self.mode = 'real'
        real_result = await self.execute_mission(mission, sim=False)

        # 3. Compare trajectories
        analysis = await self.analyze_discrepancies(sim_result, real_result)

        # 4. Generate calibration recommendations
        fixes = await self.generate_calibration_fixes(analysis)

        return {
            'sim_result': sim_result,
            'real_result': real_result,
            'analysis': analysis,
            'recommended_fixes': fixes
        }

    async def analyze_discrepancies(self, sim_result, real_result) -> dict:
        """Identify systematic differences between sim and real."""

        analysis = {}

        # Trajectory comparison
        sim_traj = np.array([(p['x'], p['y']) for p in sim_result['trajectory']])
        real_traj = np.array([(p['x'], p['y']) for p in real_result['trajectory']])

        # Calculate drift
        final_error = euclidean(sim_traj[-1], real_traj[-1])
        analysis['final_position_error'] = final_error

        # Heading error
        sim_heading = sim_result['trajectory'][-1]['theta']
        real_heading = real_result['trajectory'][-1]['theta']
        analysis['final_heading_error'] = np.abs(sim_heading - real_heading)

        # Systematic bias detection
        trajectory_diff = real_traj - sim_traj[:len(real_traj)]  # Align lengths
        analysis['mean_lateral_drift'] = np.mean(trajectory_diff[:, 1])
        analysis['mean_longitudinal_drift'] = np.mean(trajectory_diff[:, 0])

        # Speed analysis
        sim_speeds = np.array([p['speed'] for p in sim_result['trajectory']])
        real_speeds = np.array([p['speed'] for p in real_result['trajectory']])
        analysis['speed_ratio'] = np.mean(real_speeds) / np.mean(sim_speeds)

        # Rotation rate analysis
        sim_rotation = np.array([p['angular_vel'] for p in sim_result['trajectory']])
        real_rotation = np.array([p['angular_vel'] for p in real_result['trajectory']])
        analysis['rotation_ratio'] = np.mean(real_rotation) / np.mean(sim_rotation)

        # Visualize
        self.plot_comparison(sim_traj, real_traj, analysis)

        return analysis

    def plot_comparison(self, sim_traj, real_traj, analysis):
        """Generate comparison plots."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Trajectory plot
        ax1.plot(sim_traj[:, 0], sim_traj[:, 1],
                'b-', label='Simulation', linewidth=2)
        ax1.plot(real_traj[:, 0], real_traj[:, 1],
                'r--', label='Real Robot', linewidth=2)
        ax1.set_xlabel('X (m)')
        ax1.set_ylabel('Y (m)')
        ax1.set_title('Trajectory Comparison')
        ax1.legend()
        ax1.grid(True)
        ax1.axis('equal')

        # Error plot
        if len(sim_traj) == len(real_traj):
            errors = np.linalg.norm(sim_traj - real_traj, axis=1)
            ax2.plot(errors, 'g-', linewidth=2)
            ax2.set_xlabel('Time Step')
            ax2.set_ylabel('Position Error (m)')
            ax2.set_title('Trajectory Error Over Time')
            ax2.grid(True)

        plt.tight_layout()
        plt.savefig('/tmp/sim2real_comparison.png', dpi=150)
        self.get_logger().info('Saved comparison plot to /tmp/sim2real_comparison.png')

    async def generate_calibration_fixes(self, analysis: dict) -> list:
        """Use Claude to suggest calibration parameter adjustments."""

        prompt = f"""
        🤖 Sim2Real Calibration Analysis

        I ran the same navigation mission in Gazebo simulation and on the real
        OrbiBot robot. Here are the discrepancies:

        **Position Errors:**
        - Final position error: {analysis['final_position_error']:.3f} m
        - Mean lateral drift: {analysis['mean_lateral_drift']:.3f} m
        - Mean longitudinal drift: {analysis['mean_longitudinal_drift']:.3f} m

        **Heading Error:**
        - Final heading error: {np.degrees(analysis['final_heading_error']):.1f}°

        **Speed Discrepancies:**
        - Real/Sim speed ratio: {analysis['speed_ratio']:.3f}
        - Real/Sim rotation ratio: {analysis['rotation_ratio']:.3f}

        **Robot Configuration:**
        - Mecanum wheels, 50mm radius
        - Track width: 360mm, wheelbase: 260mm
        - Encoder CPR: 1320

        **Current URDF parameters (simulation):**
        ```xml
        <wheel_radius value="0.05"/>
        <wheel_separation_x value="0.26"/>
        <wheel_separation_y value="0.36"/>
        <wheel_friction value="0.8"/>
        <wheel_mass value="0.2"/>
        ```

        Based on these discrepancies, suggest specific parameter adjustments
        to improve sim2real matching. Format as JSON with:
        - parameter name
        - current value
        - suggested value
        - rationale

        Focus on wheel friction, mass distribution, and kinematic parameters.
        """

        # Call Claude via MCP
        response = await self.call_claude_mcp(prompt)

        return response['suggested_fixes']

    async def call_claude_mcp(self, prompt: str) -> dict:
        """Call Claude via MCP for analysis."""
        # Implementation depends on MCP setup
        # Simplified example:
        import anthropic

        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        response_text = message.content[0].text
        # Extract JSON from markdown code block if present
        if '```json' in response_text:
            json_str = response_text.split('```json')[1].split('```')[0].strip()
        else:
            json_str = response_text

        return json.loads(json_str)

def main():
    rclpy.init()

    agent = Sim2RealAgent()

    # Define test mission
    mission = {
        'type': 'square_path',
        'side_length': 2.0,  # meters
        'speed': 0.2  # m/s
    }

    # Run comparison
    result = agent.run_comparison_mission(mission)

    print("\n" + "="*60)
    print("SIM2REAL ANALYSIS COMPLETE")
    print("="*60)
    print(f"\nFinal position error: {result['analysis']['final_position_error']:.3f} m")
    print(f"Speed ratio (real/sim): {result['analysis']['speed_ratio']:.3f}")

    print("\n📋 Recommended Calibration Fixes:")
    for i, fix in enumerate(result['recommended_fixes'], 1):
        print(f"\n{i}. {fix['parameter']}")
        print(f"   Current: {fix['current_value']}")
        print(f"   Suggested: {fix['suggested_value']}")
        print(f"   Rationale: {fix['rationale']}")

    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

## Example Claude Analysis Output

```json
{
  "suggested_fixes": [
    {
      "parameter": "wheel_friction",
      "current_value": 0.8,
      "suggested_value": 0.72,
      "rationale": "Real robot drifts 3cm/m right, suggesting asymmetric friction. Reducing friction coefficient brings simulation closer to real carpet surface.",
      "file": "orbibot_description/urdf/orbibot.urdf.xacro",
      "line": 45
    },
    {
      "parameter": "wheel_radius",
      "current_value": 0.050,
      "suggested_value": 0.0485,
      "rationale": "Real robot travels 97% of commanded distance, indicating effective wheel radius is smaller (wear, compression, or measurement error).",
      "file": "orbibot_description/urdf/orbibot.urdf.xacro",
      "line": 32
    },
    {
      "parameter": "wheel_separation_y",
      "current_value": 0.360,
      "suggested_value": 0.355,
      "rationale": "Rotation rate is 95% of simulation, suggesting wheel track width is slightly narrower than modeled.",
      "file": "orbibot_description/urdf/orbibot.urdf.xacro",
      "line": 34
    },
    {
      "parameter": "imu_angular_velocity_stddev",
      "current_value": 0.001,
      "suggested_value": 0.005,
      "rationale": "Real IMU has more noise than simulated. Increasing noise model improves filter behavior in simulation.",
      "file": "orbibot_description/urdf/sensors.xacro",
      "line": 78
    }
  ],
  "estimated_improvement": "85% reduction in trajectory error",
  "confidence": "high",
  "next_steps": [
    "Apply suggested URDF changes",
    "Re-run comparison mission",
    "If error persists, check for motor controller deadzone"
  ]
}
```

## Automated Calibration Loop

```python
async def iterative_calibration(agent, mission, max_iterations=5,
                                 target_error=0.05):
    """Iteratively improve calibration until error threshold met."""

    for iteration in range(max_iterations):
        print(f"\n=== Calibration Iteration {iteration + 1} ===")

        # Run comparison
        result = await agent.run_comparison_mission(mission)
        error = result['analysis']['final_position_error']

        print(f"Position error: {error:.3f} m")

        if error < target_error:
            print(f"✅ Target error achieved: {error:.3f} < {target_error}")
            break

        # Apply fixes
        fixes = result['recommended_fixes']
        for fix in fixes[:2]:  # Apply top 2 fixes
            await apply_urdf_fix(fix)

        # Rebuild simulation
        subprocess.run(['ros2', 'launch', 'orbibot_gazebo',
                       'gazebo.launch.py'])

    print(f"\nCalibration complete after {iteration + 1} iterations")
```

---

[← Previous: Self-Debugging](14-self-debugging.md) | [↑ Index](README.md) | [Next: Conversational Interface →](16-conversational-interface.md)
