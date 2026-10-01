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
chmod +x "$root/.githooks/commit-msg"
git config --local core.hooksPath .githooks
echo 'Enabled commit-title and staged harness-filename validation for this checkout.'
