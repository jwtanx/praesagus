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


WINDOWS = {'five_hour': 300, 'weekly': 10080}


def finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def window(data, duration, now):
    if (not isinstance(data, dict)
            or not set(data) <= {'usedPercent', 'resetsAt', 'windowDurationMins'}
            or type(data.get('windowDurationMins')) is not int
            or data['windowDurationMins'] != duration):
        return None, None
    used = data.get('usedPercent')
    remaining = 100 - used if finite_number(used) and 0 <= used <= 100 else None
    reset = data.get('resetsAt')
    if not finite_number(reset) or reset <= now.timestamp():
        reset = None
    else:
        try:
            datetime.fromtimestamp(reset, timezone.utc)
        except (ValueError, OverflowError, OSError):
            reset = None
    return remaining, reset


def usage_windows(data, now):
    unknown = {name: (None, None) for name in WINDOWS}
    try:
        if not isinstance(data, dict):
            return unknown
        sampled = datetime.fromisoformat(data['sampled_at'].replace('Z', '+00:00'))
        if sampled.tzinfo is None or not 0 <= (now - sampled).total_seconds() <= 300:
            return unknown
        if 'schema_version' in data:
            if (type(data['schema_version']) is not int or data['schema_version'] != 2
                    or set(data) != {'schema_version', 'sampled_at', 'windows'}
                    or not isinstance(data['windows'], dict)
                    or not set(data['windows']) <= set(WINDOWS)):
                return unknown
            return {name: window(data['windows'].get(name), duration, now)
                    for name, duration in WINDOWS.items()}
        if not set(data) <= {'sampled_at', 'usedPercent', 'resetsAt', 'windowDurationMins'}:
            return unknown
        return {'five_hour': window({k: v for k, v in data.items() if k != 'sampled_at'}, 300, now),
                'weekly': (None, None)}
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
        return unknown


def usage(data, now):
    """Legacy helper: five-hour reading only; reset availability is independent."""
    return usage_windows(data, now)['five_hour']


def evaluate(data, battery_text, now):
    readings = usage_windows(data, now)
    percent = battery(battery_text)
    blockers = []
    if percent is None:
        blockers.append('battery_unknown')
    elif percent <= BATTERY_STOP_PERCENT:
        blockers.append('battery_low')
    for name, (remaining, reset) in readings.items():
        if remaining is None:
            blockers.append(name + '_usage_unknown')
        if reset is None:
            blockers.append(name + '_reset_unknown')
    constraining = [name for name, (remaining, _) in readings.items()
                   if remaining is not None and remaining <= USAGE_STOP_PERCENT]
    checkpoint = any(remaining is not None and remaining <= USAGE_CHECKPOINT_PERCENT
                     for remaining, _ in readings.values())
    if percent is not None and percent <= BATTERY_STOP_PERCENT:
        action = 'save_remove_lead_schedules'
    elif constraining:
        action = 'checkpoint_pause_until_reset'
    elif checkpoint:
        action = 'checkpoint_before_new_work'
    elif blockers:
        action = 'unknown_stop_new_work'
    else:
        action = 'ready'
    recovery = None
    if blockers:
        recovery_status = 'blocked'
    elif constraining:
        recovery_status = 'ready'
        recovery = math.ceil(max(readings[name][1] for name in constraining)) + 60
    else:
        recovery_status = 'not_required'
    return dict(battery_percent=percent,
                five_hour_remaining_percent=readings['five_hour'][0],
                reset_epoch=readings['five_hour'][1],
                weekly_remaining_percent=readings['weekly'][0],
                weekly_reset_epoch=readings['weekly'][1],
                constraining_windows=constraining, recovery_epoch=recovery,
                recovery_status=recovery_status, blockers=blockers, action=action)


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
