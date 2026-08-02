# Documentation Sync

**A doc that describes code which no longer exists is worse than no doc.**
It is confidently wrong, and it is trusted.

Every change — added, changed, **deleted** — ends with one question: *does
anything I just wrote make a document untrue?* Answer it explicitly. "Nothing
needs updating" is a valid answer; skipping the question is not.

A `Stop` hook checks this mechanically and will interrupt if code moved and no
documentation did. It is a backstop, not the rule. Do the check yourself.

---

## Documentation lives beside the code it describes

Each package carries its own set. Read them before touching the package:

| File | Holds |
|---|---|
| `src/<pkg>/README.md` | The API reference — topics, services, parameters, run commands |
| `src/<pkg>/<pkg>-issue.md` | What is currently open, with severity |
| `src/<pkg>/<pkg>-changelog.md` | What changed and **why** |

Not every package has all three; the README is the one that always exists. If a
note and the code disagree, the code decides and the note gets fixed.

## After changing anything

| If you changed… | Update |
|---|---|
| Behaviour, API, topics, services, parameters | `src/<pkg>/README.md` |
| Why something changed, or what it replaces | `src/<pkg>/<pkg>-changelog.md` |
| A finding — fixed it, made it worse, found a new one | `src/<pkg>/<pkg>-issue.md` |
| A number measured on real hardware | `src/orbibot_rosmaster_firmware/test-report.md` |
| A procedure or a pass criterion | `testing-guide.md` |
| A project-wide convention | `CLAUDE.md` — and only then |

**Measurements are documentation.** A number that stays in the terminal is a
number somebody re-measures next month. Write it down with the date **and the
conditions it was taken under** — robot elevated or on the ground, which
firmware, how many samples. `test-report.md` sections are dated for exactly
this reason: change a subsystem, re-run only that section, bump its date.

## Deleting needs more care than adding

When you remove a file, function, topic, parameter, package or skill, search for
what referenced it:

```bash
grep -rn "<name>" src/ .claude/ CLAUDE.md *.md --include=*.md
```

Fix every hit. A stale reference is not cosmetic — it sends the next reader, or
the next agent, looking for something that is gone.

Hand-maintained lists of things that exist elsewhere are the usual culprits.
Prefer a pointer to a copy.

## Why this rule is strict

All three were live in this repo, all three were confidently wrong:

- `IMPLEMENTATION_STATUS.md` advertised 15 agent tools; the registry had ~64
- `MECANUM_GUIDE.md` documented `mecanum_demo` and `mecanum_teleop` nodes that
  had never existed
- `.claude/skills/README.md` hand-listed every skill; it went stale in 20 places
  the moment seven skills were deleted, so it was replaced by a pointer
- `firmware-changelog.md` recorded "the chip produces 25644 counts/g" as a
  hardware fact. It was a register left misconfigured — and the wrong
  explanation shipped as a compensation factor for four months

None of these were caught by a build or a test. Documentation only stays true
because someone chooses to keep it true.

## Related

- `.claude/rules/git-workflow.md` — commit the doc update with the change, not after
- `.claude/rules/robot-safety.md` — measurements come from hardware, and get written down
