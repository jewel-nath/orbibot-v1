# Measurement logs

Raw CSVs from hardware runs. They exist so a number in `test-report.md` can be
re-derived instead of re-measured, and so a run that turns out to be invalid can
be *shown* to be invalid rather than quietly deleted.

| Path | Holds |
|---|---|
| `logs/*.csv` | Runs believed valid. Each carries its conditions in a `# note:` header |
| `logs/suspect/` | Runs known to be contaminated, **kept on purpose**, each with a header saying why |

`suspect/` is not a bin. A discarded run is evidence about the method — the
2026-08-05 entries there record a robot that reached a wall and was lifted
mid-profile, and a floor-budget guard that stranded the robot outside its own
boundary. Both were found by reading the log, not by watching the robot.

**A CSV without its conditions is worthless.** Robot elevated or on the ground,
battery or mains, which firmware, how many samples — the writing scripts put
these in the header, and anything added by hand should carry them too.

Written by `.claude/scripts/drive_profile.py` and
`.claude/scripts/battery_sag_log.py`.
