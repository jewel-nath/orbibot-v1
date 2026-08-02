#!/usr/bin/env bash
# SessionStart hook — record where the repo was when this session began, so the
# Stop hook can tell what THIS session changed (including work already committed).
set -uo pipefail

input=$(cat 2>/dev/null || echo '{}')
root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "${root:-}" ] && [ -d "$root/.git" ] || exit 0

session=$(printf '%s' "$input" | jq -r '.session_id // "unknown"' 2>/dev/null || echo unknown)
git -C "$root" rev-parse HEAD > "/tmp/claude-docs-sync-base-$session" 2>/dev/null || true
exit 0
