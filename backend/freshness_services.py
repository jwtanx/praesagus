"""Read-only local invocation/data status; never provider health or scheduler proof."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
import yaml
from connectors.financial.run_status import read_status, status_root, timestamp
from connectors.financial.storage import get_data_dir

POLICY_PATH = Path(__file__).resolve().parents[1] / 'ingest/config/financial_freshness.yaml'
DATASETS = ('filings', 'insider_trades', 'news', 'calendar')


def _policy(path):
    try:
        data = yaml.safe_load(Path(path).read_text())
        policy = data['filings']
        if set(policy) != {'max_success_age_seconds', 'abandoned_after_seconds'}:
            return None
        if any(type(v) is not int or not 0 < v <= 31536000 for v in policy.values()):
            return None
        return policy
    except Exception:
        return None


def _dataset(dataset, base, now):
    path = Path(base) / (dataset + '.json')
    try:
        with path.open('rb') as handle:
            raw = handle.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError()
        payload = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        rows = payload.get('records') if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ValueError()
    except FileNotFoundError:
        return {'state': 'absent', 'count': None, 'latest_data_time': None, 'time_precision': 'unknown', 'future_times': 0, 'invalid_times': 0}
    except Exception:
        return {'state': 'unreadable', 'count': None, 'latest_data_time': None, 'time_precision': 'unknown', 'future_times': 0, 'invalid_times': 0}
    valid, future, invalid = [], 0, 0
    for row in rows:
        # Calendar scheduled event time is not publication; never use ingest_ts.
        value = row.get('acceptance_datetime') if dataset in {'filings', 'insider_trades'} else row.get('published_at')
        parsed = timestamp(value)
        day = None
        if not parsed and isinstance(value, str) and len(value) == 10:
            try:
                day = date.fromisoformat(value)
            except ValueError:
                pass
        if parsed:
            if parsed > now:
                future += 1
            else:
                valid.append((parsed.date().isoformat(), parsed.isoformat(), 'timestamp'))
        elif day:
            if day > now.date():
                future += 1
            else:
                valid.append((day.isoformat(), day.isoformat(), 'date'))
        else:
            invalid += 1
    latest = max(valid) if valid else None
    return {'state': 'present' if rows else 'empty', 'count': len(rows),
            'latest_data_time': latest[1] if latest else None,
            'time_precision': latest[2] if latest else 'unknown',
            'future_times': future, 'invalid_times': invalid}


def get_freshness(*, now=None, data_dir=None, policy_path=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    now = now.astimezone(timezone.utc)
    policy = _policy(policy_path or POLICY_PATH)
    ledger, availability = None, 'unconfigured'
    try:
        root = status_root()
        if root is not None:
            ledger = read_status(root)
            availability = ledger['availability']
    except Exception:
        availability = 'unavailable'
    datasets = []
    for name in DATASETS:
        item = {'dataset': name, 'instrumented': name == 'filings',
                'ledger': availability if name == 'filings' else 'uninstrumented',
                'invocation_state': 'unknown', 'freshness': 'unknown',
                'last_attempt': None, 'last_success': None,
                'coverage': None, 'rejected': None,
                'coverage_warning': 'Invocation evidence only; source coverage and hidden connector failures are unknown.',
                'data': _dataset(name, data_dir or get_data_dir(), now),
                'policy': policy if name == 'filings' else None, 'retention': None}
        if name == 'filings' and ledger:
            runs = ledger['runs']
            item['retention'] = ledger['retention']
            if not runs:
                item['invocation_state'] = 'never-run'
            else:
                attempt = {k: v for k, v in runs[0].items() if k not in {'seq', 'dataset'}}
                state = attempt['state']
                start = timestamp(attempt['started_at'])
                if start > now or (attempt['finished_at'] and timestamp(attempt['finished_at']) > now):
                    state = 'unknown'
                elif state == 'running':
                    state = 'abandoned' if policy and (now - start).total_seconds() > policy['abandoned_after_seconds'] else ('running' if policy else 'unknown')
                attempt['state'] = state
                item['last_attempt'], item['invocation_state'] = attempt, state
                success = next((r for r in runs if r['state'] == 'succeeded' and timestamp(r['finished_at']) <= now and timestamp(r['started_at']) <= now), None)
                if success:
                    item['last_success'] = success['finished_at']
                    if policy:
                        item['freshness'] = 'recent' if (now - timestamp(success['finished_at'])).total_seconds() <= policy['max_success_age_seconds'] else 'stale'
        datasets.append(item)
    return {'read_at': now.isoformat(), 'datasets': datasets,
            'scope': 'Single-host SEC invocation metadata; other financial scripts uninstrumented; Moomoo on demand. Read time is not provider freshness.'}
