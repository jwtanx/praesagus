"""Monthly calendar ledger: initialize once, then append complete event revisions."""
import argparse
from datetime import date, datetime
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('recorded_at must be timezone-aware ISO timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('recorded_at must have timezone')
    return parsed


def validate_calendar(data, previous=None):
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('calendar schema_version must be 1')
    month = data.get('month')
    if not isinstance(month, str) or not re.fullmatch(r'\d{4}-\d{2}', month):
        raise ValueError('month must be YYYY-MM')
    first = date.fromisoformat(month + '-01')
    if data.get('timezone') != 'Asia/Kuala_Lumpur':
        raise ValueError('calendar timezone must be Asia/Kuala_Lumpur')
    if not isinstance(data.get('notes'), list):
        raise ValueError('calendar notes must be a list')
    if any(not isinstance(note, dict) or not isinstance(note.get('text'), str) for note in data['notes']):
        raise ValueError('calendar notes require structured text')
    entries = data.get('entries')
    if not isinstance(entries, list):
        raise ValueError('calendar entries must be a list')
    latest = {}
    for row in entries:
        if not isinstance(row, dict):
            raise ValueError('event revision must be an object')
        for field in ('event_id', 'date', 'title', 'time', 'summary', 'details'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError('event needs ' + field)
        for field in ('date', 'date_end'):
            if row.get(field) is not None and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', row[field]):
                raise ValueError('event dates must be YYYY-MM-DD')
        start = date.fromisoformat(row['date'])
        end = date.fromisoformat(row.get('date_end') or row['date'])
        if end < start or end < first or row['date'][:7] > month:
            raise ValueError('event must intersect ledger month')
        if row.get('kind') not in {'event', 'market-closure'} or row.get('status') not in {'scheduled', 'cancelled'}:
            raise ValueError('unknown event kind/status')
        if 'country' in row and (not isinstance(row['country'], str) or not re.fullmatch(r'[A-Z]{2}', row['country'])):
            raise ValueError('country must be an uppercase two-letter code')
        when = timestamp(row.get('recorded_at'))
        prior = latest.get(row['event_id'])
        expected = prior['revision'] + 1 if prior else 1
        if type(row.get('revision')) is not int or row['revision'] != expected:
            raise ValueError('event revisions must increase sequentially')
        if prior and when <= timestamp(prior['recorded_at']):
            raise ValueError('revision availability must increase')
        if prior or row['status'] == 'cancelled':
            if not isinstance(row.get('change_reason'), str) or not row['change_reason'].strip():
                raise ValueError('correction/cancellation requires justification')
        sources = row.get('sources')
        if not isinstance(sources, list) or not sources:
            raise ValueError('event requires source evidence')
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get('url'), str):
                raise ValueError('source needs HTTPS URL')
            url = urlsplit(source['url'])
            if url.scheme != 'https' or not url.hostname or url.username or url.password:
                raise ValueError('source needs public HTTPS URL')
        latest[row['event_id']] = row
    if previous is not None:
        validate_calendar(previous)
        if any(data.get(k) != previous.get(k) for k in ('schema_version', 'month', 'timezone', 'notes')):
            raise ValueError('existing calendar metadata cannot be rewritten')
        old = previous['entries']
        if entries[:len(old)] != old or len(entries) < len(old):
            raise ValueError('calendar history is append-only; deletion/rewrite rejected')
    return data


def append_events(existing, proposed, month, recorded_at, notes=None):
    """No absent-record deletion; unchanged complete revisions are no-ops."""
    timestamp(recorded_at)
    data = json.loads(json.dumps(existing)) if existing is not None else {
        'schema_version': 1, 'month': month, 'timezone': 'Asia/Kuala_Lumpur',
        'notes': notes or [], 'entries': []}
    validate_calendar(data)
    if data['month'] != month:
        raise ValueError('wrong ledger month')
    latest = {r['event_id']: r for r in data['entries']}
    if not isinstance(proposed, list):
        raise ValueError('updates must be event list')
    seen = set()
    for event in proposed:
        if not isinstance(event, dict) or not isinstance(event.get('event_id'), str):
            raise ValueError('updates need stable event_id')
        if event['event_id'] in seen:
            raise ValueError('duplicate update event_id')
        seen.add(event['event_id'])
        prior = latest.get(event['event_id'])
        row = {k: v for k, v in event.items() if k not in {'revision', 'recorded_at'}}
        if prior and row == {k: v for k, v in prior.items() if k not in {'revision', 'recorded_at'}}:
            continue
        row.update(revision=prior['revision'] + 1 if prior else 1, recorded_at=recorded_at)
        data['entries'].append(row)
        latest[row['event_id']] = row
    return validate_calendar(data, existing)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--month', required=True)
    parser.add_argument('--input', type=Path, required=True, help='JSON object with events and optional notes')
    parser.add_argument('--recorded-at', required=True, help='actual availability time, not a backdated report cutoff')
    parser.add_argument('--directory', type=Path, default=Path('artifacts/financial-calendar'))
    args = parser.parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}', args.month):
        parser.error('month must be YYYY-MM')
    path = args.directory / (args.month + '.json')
    old = json.loads(path.read_text()) if path.exists() else None
    payload = json.loads(args.input.read_text())
    updated = append_events(old, payload['events'], args.month, args.recorded_at, payload.get('notes'))
    if updated == old:
        print('No calendar changes; existing monthly ingestion preserved')
        return
    args.directory.mkdir(parents=True, exist_ok=True)
    # Only replace after validating the complete immutable prefix.
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)
    print('Calendar saved:', path)


if __name__ == '__main__':
    main()
