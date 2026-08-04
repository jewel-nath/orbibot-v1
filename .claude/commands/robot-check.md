# /robot-check — confirm the things software cannot check about itself

Work from [docs/operations/physical-checks.md](../../docs/operations/physical-checks.md).
It is a checklist of claims the code **cannot verify**: which physical wheel is
M4, whether the LiDAR's 0° faces forward, what the wheel radius is once 6 kg is
resting on it.

This is not `/robot-test`. That runs software against the robot. This one asks a
human to look, measure, or touch, and then writes the number down.

---

## Your job in this command

1. **Ask which section they can do right now.** They depend on where the robot
   is and what tools are within reach:

   | Section | Needs |
   |---|---|
   | **A** Look at it | nothing — no tools, no power |
   | **B** Measure it | tape, calipers, a scale |
   | **C** Power | a multimeter, and the order in `.claude/rules/robot-safety.md` |
   | **D** Powered, motors off | the stack running |
   | **E** Elevated | robot on a stool, wheels free |
   | **F** On the ground | ≥ 2 m clear floor |

2. **One item at a time.** Read out what to confirm and how. Then **stop and
   wait.** Do not batch three questions into one message — the operator answers
   the last one and the first two silently become assumptions.

3. **Ask for the number, not a yes.** "Is the wheel 100 mm?" invites a yes.
   "What do the calipers read across the wheel?" gets `98.4`. The second one
   has caught a real error before; the first cannot.

4. **Write it into the table** — the date and the value, in the `Checked` and
   `Found` columns. A row reading `2026-08-04 · 98.4 mm` is worth something next
   year. A row reading `✅` is not.

5. **If a value disagrees with the code**, say so plainly and open the finding
   in the owning package's `<pkg>-issue.md`. Do not quietly edit the config to
   match — the measurement and the change are two separate decisions, and the
   second one needs the operator.

---

## Priority order, if they ask where to start

1. **A2 — which wheel is M1/M2/M3/M4.** FW-ISSUE-4 says "M4 is 12–15 % slow"
   and that is unactionable until M4 has a physical identity. Costs one minute.
2. **A1, A3, A6** — roller pattern, LiDAR heading, BOOT0. All visual, all
   silent failures, all cheap.
3. **B1 and B2 — wheel radius, unloaded and loaded.** Every distance the robot
   reports scales by this. The loaded figure has never been recorded at all.
4. **E3 — encoder CPR by hand.** 1320 is arithmetic (11 × 30 × 4), not a
   measurement. Turn the wheel once and count.
5. **C2 before anything is plugged in.** Order matters and it can destroy the
   computer.

## Safety

Sections **C**, **E** and **F** touch power and motion. Read
`.claude/rules/robot-safety.md` first. State how to stop the robot before
anything moves, keep test speeds low, and disable motors when the item is done.

Never carry a robot-state assumption across turns. If it was elevated an hour
ago, ask again.

## When you are done

- Update the `Checked` / `Found` columns in `physical-checks.md`
- Numbers measured on hardware also go in
  `src/orbibot_rosmaster_firmware/test-report.md`, in a dated section
- Anything surprising goes in [docs/reference/field-notes.md](../../docs/reference/field-notes.md)
- Commit it. A measurement that stays in the terminal gets re-measured next
  month
