#!/usr/bin/env bash
# Stop hook — if this session changed code but no documentation, say so before
# finishing. Docs that quietly stop matching the code is this project's most
# expensive recurring bug, not a tidiness preference.
#
# Fires at most once per distinct set of undocumented code files, so it cannot
# loop and cannot nag about the same edits twice.
set -uo pipefail

input=$(cat 2>/dev/null || echo '{}')

# Claude Code sets this while it is already continuing because of a Stop hook.
[ "$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null)" = "true" ] && exit 0

root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "${root:-}" ] && [ -d "$root/.git" ] || exit 0
cd "$root" || exit 0

session=$(printf '%s' "$input" | jq -r '.session_id // "unknown"' 2>/dev/null || echo unknown)

# Everything this session touched: working tree + anything committed since start.
changed=$(git status --porcelain 2>/dev/null | sed 's/^...//;s/.* -> //')
base=$(cat "/tmp/claude-docs-sync-base-$session" 2>/dev/null || true)
if [ -n "$base" ] && git cat-file -e "$base^{commit}" 2>/dev/null; then
    changed="$changed
$(git diff --name-only "$base"..HEAD 2>/dev/null)"
fi

code=$(printf '%s\n' "$changed" | grep -E '^(src|scripts)/' | grep -vE '\.(md|txt)$' | sort -u)
docs=$(printf '%s\n' "$changed" | grep -E '(^docs/|\.md$)' | sort -u)

[ -z "$code" ] && exit 0   # no code changed — nothing to check
[ -n "$docs" ] && exit 0   # docs moved too — assume the author considered it

# Nag once per distinct file set, not once per stop.
fingerprint=$(printf '%s' "$code" | cksum | tr -d ' ')
guard="/tmp/claude-docs-sync-seen-$session-$fingerprint"
[ -f "$guard" ] && exit 0
: > "$guard"

count=$(printf '%s\n' "$code" | grep -c .)
list=$(printf '%s\n' "$code" | head -8 | sed 's/^/  - /')
[ "$count" -gt 8 ] && list="$list
  - … and $((count - 8)) more"

jq -cn --arg list "$list" --arg n "$count" '{
  decision: "block",
  reason: ("This session changed \($n) code file(s) and no documentation:\n\n\($list)\n\nBefore finishing, check whether any of these need updating — then either update them or state plainly that nothing needs to change:\n\n  src/<pkg>/README.md          API, parameters, topics, run commands\n  src/<pkg>/<pkg>-issue.md     if a finding was fixed, added, or its status moved\n  src/<pkg>/<pkg>-changelog.md why it changed, and what it replaces\n  test-report.md               if you measured something on real hardware\n  CLAUDE.md                    only if a project-wide convention changed\n\nDeleting or renaming something counts: a doc that describes code which no longer exists is worse than no doc.")
}'
