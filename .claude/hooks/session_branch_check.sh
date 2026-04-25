#!/usr/bin/env bash
# SessionStart hook: branch banner + anomaly warning.
#
# Prints a one-line status every session. Three-branch model legitimate
# resting branches are `master` (framework) and `library` (completed-works
# archive); both get a plain banner. Other branches (typically
# `extraction/{work_id}`) without a live orchestrator process are upgraded
# to a warning so the user notices an abandoned extraction and can
# `git checkout master`.
#
# Exit code is always 0 — a non-zero here would block Claude Code startup.
# See ai_context/architecture.md §Git Branch Model.

set -u

branch=$(git branch --show-current 2>/dev/null)
[ -z "$branch" ] && branch="(detached HEAD)"

if [ "$branch" = "master" ] || [ "$branch" = "library" ]; then
    printf "[git] branch: %s\n" "$branch"
    exit 0
fi

if pgrep -f 'automation\.persona_extraction' >/dev/null 2>&1; then
    printf "[git] branch: %s  (orchestrator running — extraction in progress)\n" "$branch"
    exit 0
fi

printf "[git] branch: %s  ⚠ no orchestrator process detected — possibly abandoned after crash; check and 'git checkout master'\n" "$branch"
exit 0
