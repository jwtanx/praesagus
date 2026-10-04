"""Read-only catalyst inbox over raw local financial evidence (no providers)."""
import hashlib
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DATASETS = {'filings': 'filing', 'insider_trades': 'insider_trade', 'news': 'news', 'calendar': 'calendar'}
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / 'data' / 'financial'


def _timestamp(value):
    if not value or not isinstance(value, str) or 'T' not in value and ' ' not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def safe_url(value):
    if not isinstance(value, str) or any(ord(c) <= 32 for c in value) or '\\' in value:
        return None
    try:
        parsed = urlsplit(value)
        # urlsplit defers malformed/out-of-range port validation until this access.
        parsed.port
        return value if parsed.scheme.lower() in {'http', 'https'} and parsed.hostname and not parsed.username and not parsed.password else None
    except ValueError:
        return None


def _normalize(raw, dataset, now):
    if not isinstance(raw, dict) or not raw:
        raise ValueError('record must be a nonempty object')
    fields = ('source_id', 'ticker', 'title', 'company_name', 'issuer_name', 'form_type',
              'transaction_code_label', 'transaction_code', 'reporting_owner_name', 'source_name',
              'document_url', 'filing_url', 'form_url', 'link', 'source_url', 'acceptance_datetime',
              'filing_date', 'transaction_date', 'published_at', 'first_seen_at', 'ingest_ts',
              'event_date', 'event_time', 'timezone', 'event_type')
    if any(raw.get(k) is not None and not isinstance(raw[k], str) for k in fields):
        raise ValueError('record fields must be text or null')
    gaps = []
    kind = DATASETS[dataset]
    source_id = raw.get('source_id') or None
    canonical = json.dumps(raw, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    record_id = dataset + ':' + ('source:' + source_id if source_id else 'sha256:' + hashlib.sha256(canonical.encode()).hexdigest())
    if not source_id:
        gaps.append('source_id unavailable; exact-record hash used')
    ticker = (raw.get('ticker') or '').strip().upper() or None
    if not ticker:
        gaps.append('ticker unavailable (may be a global event)')
    metadata = raw.get('metadata')
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError('metadata must be an object')
    if kind == 'filing':
        candidate = raw.get('acceptance_datetime') or raw.get('filing_date')
        published = raw.get('acceptance_datetime')
        available = raw.get('acceptance_datetime')
        url_candidates = [raw.get('document_url'), raw.get('filing_url')]
        source = 'SEC'
        title = f"{raw.get('company_name') or ticker or 'Company'} · {raw.get('form_type') or 'SEC filing'}"
        subtype = raw.get('form_type')
    elif kind == 'insider_trade':
        candidate = raw.get('transaction_date')
        published = raw.get('acceptance_datetime')
        available = raw.get('acceptance_datetime')
        url_candidates = [raw.get('document_url'), raw.get('form_url')]
        source = 'SEC'
        title = f"{raw.get('reporting_owner_name') or 'Insider'} · {raw.get('transaction_code_label') or raw.get('transaction_code') or 'transaction'} · {ticker or raw.get('issuer_name') or 'Company'}"
        subtype = raw.get('transaction_code')
    elif kind == 'news':
        candidate = raw.get('published_at')
        published, available = raw.get('published_at'), raw.get('first_seen_at')
        url_candidates = [raw.get('link')]
        source = raw.get('source_name') or None
        title = raw.get('title') or f"{ticker or 'Company'} news"
        subtype = None
    else:
        candidate = raw.get('event_date')
        published, available = raw.get('published_at'), raw.get('first_seen_at')
        url_candidates = [raw.get('source_url'), metadata.get('source_url')]
        source = raw.get('source_name') or None
        subtype = raw.get('event_type')
        title = raw.get('title') or f"{ticker or 'Global'} · {subtype or 'calendar event'}"
        if raw.get('event_time'):
            candidate = (candidate or '') + 'T' + raw['event_time']
            if not _timestamp(candidate):
                try:
                    local = datetime.fromisoformat(candidate)
                    zone = ZoneInfo(raw.get('timezone') or '')
                    aware = local.replace(tzinfo=zone)
                    # Reject nonexistent/ambiguous wall times rather than choosing a DST fold.
                    if aware.utcoffset() != aware.replace(fold=1).utcoffset() or aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != local:
                        raise ValueError('ambiguous calendar time')
                    candidate = aware.isoformat()
                except (ValueError, ZoneInfoNotFoundError):
                    gaps.append('calendar timezone missing/invalid or local time ambiguous')
    url = next((safe_url(v) for v in url_candidates if safe_url(v)), None)
    if not url:
        gaps.append('source_url unavailable or unsafe')
    if not source:
        gaps.append('source provider unavailable')
    parsed = _timestamp(candidate)
    day = _date(candidate)
    event_at, precision, zone = None, 'unknown', None
    scheduled = False
    if parsed:
        if kind != 'calendar' and parsed > now:
            gaps.append('event_at is future observed information; excluded from dated feed')
        else:
            event_at, precision, zone = parsed.isoformat(), 'timestamp', 'UTC'
            scheduled = kind == 'calendar' and parsed > now
    elif day:
        if kind != 'calendar' and day > now.date():
            gaps.append('event_at is a future observed date; excluded from dated feed')
        else:
            event_at, precision = day.isoformat(), 'date'
            zone = raw.get('timezone') if kind == 'calendar' else None
            today = now.date()
            if zone:
                try:
                    today = now.astimezone(ZoneInfo(zone)).date()
                except (ValueError, ZoneInfoNotFoundError):
                    gaps.append('calendar timezone invalid; schedule compares UTC dates')
            scheduled = kind == 'calendar' and day > today
            if not zone:
                gaps.append('event timezone unavailable; date precision retained')
    else:
        gaps.append('event_at missing, invalid or timezone-naive')
    ingested = raw.get('ingest_ts') or None
    for field, value in [('published_at', published), ('available_at', available), ('ingested_at', ingested)]:
        if not value:
            gaps.append(field + ' unavailable')
        elif not _timestamp(value):
            gaps.append(field + ' invalid or timezone-naive; original retained')
        elif _timestamp(value) > now:
            gaps.append(field + ' is future; original retained')
    for earlier_name, earlier, later_name, later in (
        ('available_at', available, 'published_at', published),
        ('ingested_at', ingested, 'available_at', available),
    ):
        if _timestamp(earlier) and _timestamp(later) and _timestamp(earlier) < _timestamp(later):
            gaps.append(earlier_name + ' precedes ' + later_name + '; source discrepancy retained')
    return {
        'id': record_id, 'source_id': source_id, 'event_type': kind, 'subtype': subtype,
        'ticker': ticker, 'title': title, 'source': source, 'source_url': url,
        'event_at': event_at, 'time_precision': precision, 'timezone': zone,
        'raw_event_at': raw.get('transaction_date') if kind == 'insider_trade' else
                        raw.get('published_at') if kind == 'news' else
                        raw.get('acceptance_datetime') or raw.get('filing_date') if kind == 'filing' else
                        {'event_date': raw.get('event_date'), 'event_time': raw.get('event_time'), 'timezone': raw.get('timezone')},
        'published_at': published or None, 'available_at': available or None,
        'ingested_at': ingested, 'scheduled': scheduled,
        'estimated': raw.get('estimated') if isinstance(raw.get('estimated'), bool) else None,
        'data_gaps': gaps,
    }, canonical


def _sort_key(record):
    event = record['event_at']
    stamp = _timestamp(event)
    day = _date(event)
    # A numeric date key does not invent timestamp precision in the exposed item.
    key = stamp.timestamp() if stamp else (day.toordinal() - date(1970, 1, 1).toordinal()) * 86400 if day else 0
    return (0 if record['scheduled'] else 1 if event else 2,
            key if record['scheduled'] else -key, record['id'])


def get_catalysts(ticker=None, event_type=None, limit=50, offset=0, now=None, data_dir=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    now = now.astimezone(timezone.utc)
    base = Path(data_dir or os.getenv('PRAESAGUS_FINANCIAL_DATA_DIR', DEFAULT_DATA_DIR))
    records, statuses = [], {}
    for dataset in DATASETS:
        status = {'status': 'loaded', 'rows_read': 0, 'rows_skipped': 0, 'duplicates_removed': 0}
        statuses[dataset] = status
        try:
            payload = json.loads((base / (dataset + '.json')).read_text(encoding='utf-8'),
                                 parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
            rows = payload.get('records') if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                raise ValueError('records must be a list')
        except FileNotFoundError:
            status['status'] = 'absent'
            continue
        except (OSError, UnicodeError, ValueError):
            status['status'] = 'unreadable'
            status['warning'] = 'Dataset could not be read as a JSON record list'
            continue
        selected = {}
        status['rows_read'] = len(rows)
        for raw in rows:
            try:
                record, canonical = _normalize(raw, dataset, now)
            except (ValueError, TypeError, OverflowError):
                status['rows_skipped'] += 1
                continue
            ingestion = _timestamp(record['ingested_at'])
            rank = (ingestion.timestamp() if ingestion and ingestion <= now else float('-inf'), canonical)
            prior = selected.get(record['id'])
            if prior:
                status['duplicates_removed'] += 1
            if not prior or rank > prior[0]:
                selected[record['id']] = (rank, record)
        records.extend(item[1] for item in selected.values())
        status['records_loaded'] = len(selected)
    ticker = ticker.strip().upper() if ticker else None
    filtered = [r for r in records if (not ticker or r['ticker'] == ticker) and
                (not event_type or r['event_type'] == event_type)]
    filtered.sort(key=_sort_key)
    page = filtered[offset:offset + limit]
    return {'records': page, 'count': len(page), 'total': len(filtered), 'limit': limit,
            'offset': offset, 'retrieved_at': now.isoformat(), 'dataset_status': statuses}
