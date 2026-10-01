"""Read-only resource probe. Supply sanitized usage metadata, never credentials."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import subprocess

BATTERY_STOP_PERCENT = 8
USAGE_STOP_PERCENT = 2
USAGE_CHECKPOINT_PERCENT = 5


def battery(text):
    values = re.findall(r"\b(\d{1,3})%;", text)
    if len(values) != 1 or not 0 <= int(values[0]) <= 100:
        return None
    return int(values[0])


def usage(data, now):
    try:
        used = data['usedPercent']
        reset = data['resetsAt']
        sampled = datetime.fromisoformat(data['sampled_at'].replace('Z', '+00:00'))
        if (isinstance(used, bool) or not isinstance(used, (int, float))
                or not math.isfinite(used) or not 0 <= used <= 100
                or isinstance(reset, bool) or not isinstance(reset, (int, float))
                or not math.isfinite(reset) or reset <= now.timestamp()
                or data['windowDurationMins'] != 300 or sampled.tzinfo is None
                or not 0 <= (now - sampled).total_seconds() <= 300):
            return None, None
        return 100 - used, int(reset)
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
        return None, None


def evaluate(data, battery_text, now):
    remaining, reset = usage(data, now)
    percent = battery(battery_text)
    if percent is not None and percent <= BATTERY_STOP_PERCENT:
        action = 'save_remove_lead_schedules'
    elif remaining is not None and remaining <= USAGE_STOP_PERCENT:
        action = 'checkpoint_pause_until_reset'
    elif percent is None or remaining is None:
        action = 'unknown_stop_new_work'
    elif remaining <= USAGE_CHECKPOINT_PERCENT:
        action = 'checkpoint_before_new_work'
    else:
        action = 'ready'
    return dict(battery_percent=percent, five_hour_remaining_percent=remaining,
                reset_epoch=reset, action=action)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--usage-json', type=Path)
    args = parser.parse_args()
    data = {}
    if args.usage_json:
        try:
            data = json.loads(args.usage_json.read_text())
        except (OSError, ValueError):
            pass
    try:
        result = subprocess.run(['pmset', '-g', 'batt'], capture_output=True,
                                text=True, timeout=5, check=True)
        text = result.stdout
    except (OSError, subprocess.SubprocessError):
        text = ''
    print(json.dumps(evaluate(data, text, datetime.now(timezone.utc)), separators=(',', ':')))


if __name__ == '__main__':
    main()
