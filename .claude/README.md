# OrbiBot Claude Code Configuration

Claude Code settings, rules, skills, and helper scripts for OrbiBot development.

## Structure

```
.claude/
├── CLAUDE.md              # Main project instructions (loaded automatically)
├── settings.json          # Shared permissions (committed to git)
├── settings.local.json    # Local hooks and permissions
├── commands/
│   └── ros2.md            # ROS 2 command reference
├── rules/
│   ├── robot_specific.md  # OrbiBot hardware, TF tree, mecanum kinematics
│   ├── ros2_general.md    # ROS 2 conventions, package structure
│   ├── ros2_nodes.md      # Node patterns (pub/sub, service, action, lifecycle)
│   ├── ros2_communication.md  # Topic naming, QoS profiles, messages
│   ├── clean_architecture.md  # Clean Architecture layer rules
│   └── testing.md         # Unit, integration, E2E test patterns
├── skills/
│   ├── ros2_node_creation/    # Node templates
│   ├── ros2_launch_config/    # Launch file patterns
│   ├── ros2_service_action/   # Service/Action patterns
│   ├── ros2_messaging/        # Pub/Sub patterns
│   ├── ros2_testing/          # Test strategies
│   ├── ros2_lifecycle/        # Lifecycle Node templates
│   ├── ros2_transforms/       # TF2 patterns
│   ├── ros2_diagnostics/      # Health monitoring
│   └── ros2_bag/              # Bag recording utilities
└── scripts/
    ├── preflight.sh       # Pre-flight check before operating
    ├── motor.sh           # Quick motor test
    ├── diag.sh            # System diagnostic
    ├── safety.sh          # Safety parameter validation
    └── encoder.sh         # Encoder troubleshooting
```

## Scripts

Run from workspace root:

```bash
bash .claude/scripts/preflight.sh   # Before operating robot
bash .claude/scripts/motor.sh       # Test motors
bash .claude/scripts/diag.sh        # System diagnostic
bash .claude/scripts/safety.sh      # Validate safety params
bash .claude/scripts/encoder.sh     # Debug encoder issues
```

## Hooks

Configured in `settings.local.json`:

| Hook | Action |
|------|--------|
| SessionStart | Show workspace info, check hardware connection |
| UserPromptSubmit | Warn if staged git changes |
| PostToolUse | Remind to source after colcon builds |
