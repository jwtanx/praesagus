#!/bin/sh
# Usage remains an app-tool input; this wrapper never reads broker/auth secrets.
set -eu
task_script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$task_script_dir/status.py" "$@"
