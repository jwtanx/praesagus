#!/bin/sh
set -eu
root=$(git rev-parse --show-toplevel)
current=$(git config --get core.hooksPath || true)
if [ -n "$current" ] && [ "$current" != '.githooks' ]; then
    echo "Existing hooksPath ($current) preserved; integrate hooks manually." >&2
    exit 1
fi
if [ -z "$current" ]; then
    hooks=$(git rev-parse --git-path hooks)
    for hook in "$hooks"/*; do
        case "$hook" in *.sample) continue ;; esac
        if [ -f "$hook" ] && [ -x "$hook" ]; then
            echo 'Existing executable Git hooks preserved; integrate manually.' >&2
            exit 1
        fi
    done
fi
for hook in commit-msg pre-commit pre-push run-tests; do
    chmod +x "$root/.githooks/$hook"
done
git config --local core.hooksPath .githooks
echo 'Enabled full-test commit/push gates, commit-title and staged harness-filename validation for this checkout.'
