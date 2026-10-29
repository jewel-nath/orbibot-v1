# Contributing

At Orbitax, I build OrbiBot in my free time; V1 is its first robot. Issues
and pull requests are welcome. This page is how the code and its
documentation are kept in step.

## The code decides

When a document disagrees with the code, the document is wrong. A doc that
describes code which no longer exists is worse than no doc: it is confidently
wrong, and it is trusted. So every change, deletions included, ends with one
question: *does this make any document untrue?*

## Where documentation lives

Beside the code it describes:

| File | Holds |
|---|---|
| `src/<package>/README.md` | Topics, services, parameters, launch files, and the package's status |
| `src/<package>/CHANGELOG.md` | What changed and why (where the package keeps one) |
| `src/<package>/known-issues.md` | What is open, with its severity |
| `src/orbibot_rosmaster_firmware/test-report.md` | What was tested on the hardware, dated, with the robot's state |

`docs/` holds what belongs to the robot as a whole: [the index](docs/README.md)
lists it.

## After a change, update

| If you changed… | Update |
|---|---|
| Behaviour, an API, topics, services, parameters, launch files | The package's `README.md` |
| Why something changed, or what it replaces | The package's `CHANGELOG.md` |
| A known issue: fixed one, found one, or it got worse | The package's `known-issues.md` |
| A number measured on the robot | `test-report.md`, or [docs/status.md](docs/status.md) |
| A test procedure or a pass criterion | [docs/testing/README.md](docs/testing/README.md) |

When you remove or rename something, search for what referred to it and fix
every hit:

```bash
grep -rn "<name>" src/ docs/ .claude/ README.md CLAUDE.md --include=*.md
```

## Numbers

- Write a measurement down with its date and the robot's state: wheels off
  the ground, or driving on the floor. A motion number taken with the wheels
  in the air proves direction and sign, not distance or drift.
- A number worked out from a datasheet or a config is not a measurement:
  say which it is.

## Code

- Python: `snake_case` functions and files, `PascalCase` classes,
  `UPPER_SNAKE_CASE` constants. C: the same, in `snake_case.c` files.
  Docs: `kebab-case.md`. More in `.claude/rules/code-style.md`.
- The base frame is `base_footprint`; standard topics stay flat (`/cmd_vel`,
  `/scan`, `/odom`); OrbiBot's own topics take the `/orbibot/` prefix.
- Each package launches only its own nodes; launch files that start several
  packages belong in `orbibot_bringup`.
- Build the workspace, and the firmware if you touched it, before a pull
  request:

  ```bash
  colcon build --symlink-install
  cd src/orbibot_rosmaster_firmware && ~/.platformio/penv/bin/pio run
  ```

## Safety

Anything that moves the wheels runs on a real robot. Read
[the safety rules](.claude/rules/robot-safety.md) before testing motion or
flashing the firmware.

## Licence

By contributing, you agree that your contribution is licensed under the
[Apache License 2.0](LICENSE), as the rest of the repository.
