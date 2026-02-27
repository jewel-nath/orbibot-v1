# ROS2 Package README Workflow Rules

## Before Reading or Editing Any ROS2 Package

**MUST** first read the package's `README.md` file:
- Path pattern: `src/<package_name>/README.md`

## After Editing Any ROS2 Package

If the changes affect:
- Package functionality
- API/interfaces
- Launch files or configuration
- Dependencies

**MUST** update the package's `README.md` to reflect:
- New features or changes
- Modified parameters or topics
- Updated usage instructions
- New dependencies

## Understanding the Full Codebase

**MUST** first read `CLAUDE.md` at the project root before exploring the entire codebase.

## Quick Reference: ROS2 Package README.md Locations

```
src/orbibot_ai/README.md
src/orbibot_bringup/README.md
src/orbibot_description/README.md
src/orbibot_exploration/README.md
src/orbibot_hardware/README.md
src/orbibot_localization/README.md
src/orbibot_mcp_server/README.md
src/orbibot_msgs/README.md
src/orbibot_navigation/README.md
src/orbibot_sensors/README.md
src/orbibot_slam/README.md
src/orbibot_teleop/README.md
src/orbibot_webgui/README.md
src/orbibot_rosmaster_firmware/README.md
```

## Global Context

- **CLAUDE.md**: Project-wide architecture and guidelines

## Workflow Checklist

When working with any package:
- [ ] Read package README.md first
- [ ] Make necessary edits
- [ ] Update README.md if changes affect functionality/docs
- [ ] Reference CLAUDE.md for architectural context