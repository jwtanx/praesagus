#!/bin/sh
# Manual reviewed-input export only; no collection, training or admission creation.
set -eu

launcher_fail() {
    printf '{"status":"failed","reason":"%s"}\n' "$1"
    exit 1
}

if [ "$#" -eq 1 ] && [ "$1" = '--help' ]; then
    printf '%s\n' 'Usage: sh scripts/daily-market-brief/run_private_forecast.sh --batch /absolute/private/batch.json --output-parent /absolute/private/exports'
    exit 0
fi

launcher_batch=''
launcher_output=''
while [ "$#" -gt 0 ]; do
    case "$1" in
        --batch)
            [ "$#" -ge 2 ] && [ -z "$launcher_batch" ] && [ -n "$2" ] || launcher_fail arguments-invalid
            launcher_batch=$2
            ;;
        --output-parent)
            [ "$#" -ge 2 ] && [ -z "$launcher_output" ] && [ -n "$2" ] || launcher_fail arguments-invalid
            launcher_output=$2
            ;;
        *) launcher_fail arguments-invalid ;;
    esac
    shift 2
done
[ -n "$launcher_batch" ] && [ -n "$launcher_output" ] || launcher_fail arguments-invalid

launcher_root=$(CDPATH='' cd -P "$(dirname "$0")/../.." 2>/dev/null && pwd) || launcher_fail interpreter-unavailable
if launcher_python=$(git -C "$launcher_root" config --get praesagus.testPython 2>/dev/null); then
    launcher_python=${launcher_python:-python3}
else
    [ "$?" -eq 1 ] || launcher_fail interpreter-unavailable
    launcher_python=python3
fi
command -v "$launcher_python" >/dev/null 2>&1 || launcher_fail interpreter-unavailable
if ! "$launcher_python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    launcher_fail interpreter-unsupported
fi

exec "$launcher_python" - "$launcher_root" "$launcher_batch" "$launcher_output" <<'PY'
import json
import sys

stage = 'exporter-unavailable'
try:
    import importlib.util
    import os
    from datetime import datetime, timezone
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        '_manual_private_export', Path(sys.argv[1]) / 'scripts/daily-market-brief/prepare_private_forecast.py')
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)

    stage = 'private-input-invalid'
    payload = exporter.private_io.read_private_json(sys.argv[2], max_depth=12)
    parent = exporter.private_io._path(sys.argv[3])
    exporter.need(not (parent / '.git').exists())
    descriptor = exporter.private_io._directory(parent)
    os.close(descriptor)

    stage = 'preparation-invalid'
    stamp = datetime.now(timezone.utc).isoformat()
    result = exporter.prepare_export(payload, batch_mode=True, issued_at=stamp, report_cutoff=stamp)
    stage = 'private-write-failed'
    folder = exporter.write_export(str(parent), result)
    print(json.dumps(dict(status='prepared' if result['counts']['generated'] else 'withheld',
                          counts=result['counts'], csv_path=str(folder / 'forecasts.csv'))))
except Exception:
    # Fail closed even for an unexpected adapter/import error; never print input or exception text.
    print(json.dumps(dict(status='failed', reason=stage)))
    sys.exit(1)
PY
