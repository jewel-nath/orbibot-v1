# Mandatory Workflow Rules

**These rules are NON-NEGOTIABLE. Failure to follow them is unacceptable.**

## 1. Commit After Every Feature/Fix

- **ALWAYS** create a git commit immediately after completing a feature, bug fix, or logical unit of work
- Do NOT batch multiple unrelated changes into one commit
- Do NOT continue to the next task without committing the current one
- If the user asks to implement something, the task is NOT complete until committed
- Use descriptive commit messages that explain the "why"

**Commit checklist before moving on:**
```
✓ Code changes complete
✓ Files staged (git add)
✓ Commit created with descriptive message
✓ THEN move to next task
```

## 2. Follow Naming Conventions Strictly

- **ALWAYS** read `.claude/rules/code-style.md` before writing ANY code
- Python: `PascalCase` for classes, `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants
- C: `snake_case` for functions/variables, `snake_case_t` for types, `UPPER_SNAKE_CASE` for macros
- Files: `snake_case.py`, `snake_case.c`, `kebab-case.md`
- **NEVER** use `__double_underscore` for private members (use `_single_underscore`)
- **NEVER** use underscores in class names (use `OrbiBotControlManager`, not `OrbiBot_Control_Manager`)

**Before writing code, verify:**
```
✓ Class names are PascalCase
✓ Functions/methods are snake_case
✓ Constants are UPPER_SNAKE_CASE at module level
✓ Private members use _single_underscore
```
