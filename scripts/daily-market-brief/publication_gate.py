"""Fail-closed publication checks. Reads staged evidence; never fetches or writes it."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from ingest.daily_report_projection import validate_market_rights
from ingest.forecast_scenario import build_forecast_scenario, apply_scenario_to_row
from ingest.private_market_store import parse_aware

REPORTS = 'artifacts/daily-market-brief/'
US = 'SPY QQQ IWM JPM GS V AAPL MSFT GOOGL NVDA TSM AVGO LLY JNJ ABT WMT PG KO TSLA HD MCD XOM COP SLB CAT GE UPS LIN FCX NEM'.split()
MY = '0820EA 0800EA 1155 1023 0277 0259 0166 0097 5225 5878 4707 3689 5296 4715 6033 5681 5246 3816 1961 5285'.split()
FIXED = frozenset([('US', t, 'USD') for t in US] + [('MY', t, 'MYR') for t in MY])
IDENTITY = ('market', 'ticker', 'currency')
MAX_EVIDENCE = 2 * 1024 * 1024


class PublicationError(ValueError):
    """Only controlled messages may escape the private evidence boundary."""


def require(ok, message):
    if not ok:
        raise PublicationError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def identity(row):
    return tuple(row.get(k) for k in IDENTITY)


def publication_time(value):
    try:
        result = parse_aware(value)
        require(result.utcoffset().total_seconds() == 0, 'publication cutoff must be aware UTC')
        return result
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise PublicationError('publication cutoff must be aware UTC') from None


def positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def aggregate_pairs(rows, price_ids, forecast_ids):
    """Pure set arithmetic, with no production eligibility override or threshold option."""
    ids = [identity(row) for row in rows]
    require(len(ids) == 50 and len(set(ids)) == 50 and set(ids) == FIXED,
            'publication requires exactly the fixed 50 identities')
    require(set(price_ids) <= FIXED and set(forecast_ids) <= FIXED, 'unknown eligible identity')
    paired = set(price_ids) & set(forecast_ids)
    return {'eligible_pairs': len(paired), 'denominator': 50, 'required_pairs': 35,
            'passed': len(paired) >= 35}


def _no_duplicates(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, 'duplicate evidence field')
        result[k] = v
    return result


def read_evidence(directory, day):
    """Open each component without following links; require private owner-only staging."""
    require(directory is not None, 'publication evidence directory is required')
    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) is not None, 'invalid evidence date')
    date.fromisoformat(day)
    folder = Path(directory)
    require(folder.is_absolute() and folder == folder.resolve() and not folder.is_relative_to(REPO),
            'evidence directory must be an absolute external path without links')
    fd = None
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        for part in folder.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
                'evidence directory must be private and owned')
        child = os.open(day + '.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(child, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and stat.S_IMODE(info.st_mode) in (0o400, 0o600)
                    and 0 < info.st_size <= MAX_EVIDENCE, 'invalid private evidence file')
            raw = stream.read(MAX_EVIDENCE + 1)
        require(len(raw) <= MAX_EVIDENCE, 'evidence size limit exceeded')
        return json.loads(raw, object_pairs_hook=_no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (OSError, ValueError, TypeError, RecursionError):
        raise PublicationError('private publication evidence unavailable or invalid') from None
    finally:
        if fd is not None:
            os.close(fd)


def row_eligibility(row, item, report_cutoff, published_at):
    """Replay existing public admission, then independently bind the displayed close."""
    try:
        require(type(item) is dict and set(item) == {
            *IDENTITY, 'quote', 'quote_rights', 'evidence', 'admission', 'result_sha256'}, 'invalid row evidence')
        require(identity(item) == identity(row) and identity(row) in FIXED, 'identity mismatch')
        require(row.get('forecast_status') == 'available' and row.get('quote_status') == 'observed'
                and row.get('confidence') in ('low', 'medium', 'high')
                and all(positive(row.get(k)) for k in ('current_price_value', 'estimated_mid_case_value',
                                                     'range_low_value', 'range_high_value')),
                'numeric support unavailable')
        require(row['range_low_value'] <= row['estimated_mid_case_value'] <= row['range_high_value'],
                'unordered numeric support')
        cutoff = parse_aware(report_cutoff)
        issue = parse_aware(row['forecast_as_of'])
        require(issue <= cutoff <= published_at, 'future issuance or report cutoff')
        result = build_forecast_scenario(item['evidence'], admission=item['admission'],
                                        issued_at=row['forecast_as_of'], report_cutoff=report_cutoff)
        require(result['status'] == 'generated' and digest(result) == item['result_sha256'],
                'public forecast admission failed')
        mapped = apply_scenario_to_row(row, result, identity=dict(zip(IDENTITY, identity(row))))
        require(mapped == row, 'forecast fields differ from admitted result')
        e = item['evidence']
        instrument, calendar = e['instrument'], e['calendar']
        require(all(instrument[k] == row[k] for k in IDENTITY), 'forecast instrument mismatch')
        audit = result['private_audit']
        require(published_at < parse_aware(audit['target_close_at']), 'forecast target expired')
        zone = ZoneInfo(calendar['timezone'])
        local_day = published_at.astimezone(zone).date()
        require(date.fromisoformat(calendar['coverage_start']) <= local_day
                <= date.fromisoformat(calendar['coverage_end']), 'publication calendar coverage missing')
        sessions = sorted((parse_aware(s['regular_close_at']), s['session_date']) for s in calendar['sessions'])
        completed = [(t, d) for t, d in sessions if t <= published_at]
        require(completed and any(t > published_at for t, _ in sessions), 'publication calendar window incomplete')
        close_at, session = completed[-1]
        require(session == audit['reference_session'], 'stale forecast reference session')
        q = item['quote']
        require(type(q) is dict and set(q) == {'price', 'currency', 'provider', 'source_field', 'source_url',
                    'session_date', 'source_at', 'observed_at', 'ingested_at', 'known_at'}, 'invalid price evidence')
        bars = [b for b in e['bars'] if b['session_date'] == session]
        require(len(bars) == 1, 'price reference unavailable')
        bar = bars[0]
        require(positive(q['price']) and q['price'] == row['current_price_value'] == bar['close']
                and q['currency'] == row['currency'] == bar['currency']
                and q['session_date'] == session and q['provider'] == e['source']['provider'] == 'moomoo-rest'
                and q['source_field'] == e['source']['source_field']
                and q['source_url'] == bar['source_url'], 'price source/session/value mismatch')
        require(any(type(s) is dict and s.get('url') == q['source_url'] for s in row.get('sources', [])),
                'displayed price source link missing')
        times = [parse_aware(q[k]) for k in ('source_at', 'observed_at', 'ingested_at', 'known_at')]
        require(close_at <= times[0] <= times[1] <= times[2] <= times[3] <= cutoff <= published_at
                and parse_aware(bar['known_at']) <= times[3]
                and parse_aware(row['price_as_of']) == times[0], 'price availability mismatch')
        # Existing validator excludes MY and other providers. This must stay fail-closed.
        validate_market_rights(item['quote_rights'], published_at.isoformat(),
                               markets=(row['market'],), fields={'quote.price', 'source.timestamps'})
        return True
    except (ValueError, TypeError, KeyError, OverflowError, AttributeError):
        return False


def validate_publication(report, report_bytes, evidence, published_at):
    """Structural validation remains a separate caller gate; evidence is never returned."""
    try:
        rows = report['forecasts']
        aggregate_pairs(rows, set(), set())
        require(type(evidence) is dict and set(evidence) == {'schema_version', 'report_sha256', 'rows'}
                and type(evidence['schema_version']) is int and evidence['schema_version'] == 1
                and evidence['report_sha256'] == hashlib.sha256(report_bytes).hexdigest()
                and type(evidence['rows']) is list and len(evidence['rows']) <= 50,
                'evidence must bind the exact report bytes')
        items = {}
        for item in evidence['rows']:
            key = identity(item)
            require(key in FIXED and key not in items, 'duplicate or unknown evidence identity')
            items[key] = item
        eligible = {identity(row) for row in rows if identity(row) in items
                    and row_eligibility(row, items[identity(row)], report['metadata']['as_of'], published_at)}
        summary = aggregate_pairs(rows, eligible, eligible)
        require(summary['passed'], f'publication blocked: {summary["eligible_pairs"]}/50 eligible pairs; require 35/50')
        return summary
    except PublicationError:
        raise
    except (ValueError, TypeError, KeyError, OverflowError, AttributeError):
        raise PublicationError('publication evidence contract invalid') from None


def git(repo, *argv):
    result = subprocess.run(['git', '-C', str(repo), *argv], capture_output=True, timeout=15)
    require(result.returncode == 0, 'publication Git evidence unavailable')
    return result.stdout


def changed_editions(repo, base, head='HEAD'):
    """No base means initial/manual delivery: validate latest, never all expired archives."""
    head = git(repo, 'rev-parse', '--verify', head + '^{commit}').decode().strip()
    index_path = REPORTS + 'reports.json'
    current = json.loads(git(repo, 'show', head + ':' + index_path))
    selected = set()
    if base is None or re.fullmatch('0{40}|0{64}', base):
        selected.add(current['latest'])
    else:
        require(re.fullmatch('[a-fA-F0-9]{40}|[a-fA-F0-9]{64}', base) is not None,
                'publication base must be a full commit ID')
        base = git(repo, 'rev-parse', '--verify', base + '^{commit}').decode().strip()
        names = git(repo, 'diff', '--name-only', '--diff-filter=ACMRT', '--no-renames', '-z', base, head, '--', REPORTS)
        paths = set(names.decode().rstrip('\0').split('\0'))
        for path in paths:
            match = re.fullmatch(re.escape(REPORTS) + r'(?:market-snapshots/)?(\d{4}-\d{2}-\d{2})\.json', path)
            if match:
                selected.add(match[1])
        if index_path in paths:
            old = git(repo, 'ls-tree', '--name-only', base, '--', index_path).strip()
            previous = json.loads(git(repo, 'show', base + ':' + index_path)) if old else {'reports': []}
            old_dates = {r['date'] for r in previous['reports']}
            selected.update(r['date'] for r in current['reports'] if r['date'] not in old_dates)
            if previous.get('latest') != current['latest']:
                selected.add(current['latest'])
        if any(path.startswith(REPORTS + 'watchlist-universe') for path in paths):
            selected.add(current['latest'])
    require(all(type(day) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) for day in selected),
            'invalid publication edition')
    for day in selected:
        date.fromisoformat(day)
    return sorted(selected)


def event_base(repo, event_name, event):
    if event_name == 'pull_request':
        base = event['pull_request']['base']['sha']
        require(re.fullmatch('[a-fA-F0-9]{40}|[a-fA-F0-9]{64}', base) is not None, 'invalid PR base')
        return git(repo, 'merge-base', base, 'HEAD').decode().strip()
    if event_name == 'push':
        require('before' in event, 'missing push base')
        return event['before']
    require(event_name == 'workflow_dispatch', 'unsupported publication event')
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--publication-at', required=True, help='actual workflow publication cutoff, aware UTC')
    ap.add_argument('--publication-evidence-dir', type=Path)
    ap.add_argument('--date')
    ap.add_argument('--base')
    ap.add_argument('--github-event', action='store_true')
    ap.add_argument('--deployment-base', help='last successful Pages workflow commit; requires --github-event')
    args = ap.parse_args(argv)
    published = publication_time(args.publication_at)
    require(abs((datetime.now(timezone.utc) - published).total_seconds()) <= 300,
            'publication cutoff must be captured at this delivery, within five minutes')
    require(not (args.date and (args.base or args.github_event)), 'choose date or Git publication selection')
    base = args.base
    require(args.deployment_base is None or args.github_event, 'deployment base requires GitHub event selection')
    if args.github_event:
        require(args.base is None, 'choose one publication base source')
        event_path = Path(os.environ['GITHUB_EVENT_PATH'])
        require(event_path.stat().st_size <= MAX_EVIDENCE, 'event size limit exceeded')
        base = event_base(REPO, os.environ['GITHUB_EVENT_NAME'], json.loads(event_path.read_text()))
        if args.deployment_base is not None and os.environ['GITHUB_EVENT_NAME'] == 'push':
            require(re.fullmatch('[a-fA-F0-9]{40}|[a-fA-F0-9]{64}', args.deployment_base) is not None,
                    'last successful deployment base is required')
            base = args.deployment_base
    days = [args.date] if args.date else changed_editions(REPO, base)
    import validate_report_json as validator
    universe_path = REPO / REPORTS / 'watchlist-universe-five.json'
    universe = validator.read_json(universe_path)
    keys, members = validator.validate_universe(universe_path, universe)
    u = (universe['effective_from'], keys, members, universe['taxonomy_id'], universe['groups'])
    for day in days:
        require(type(day) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) is not None, 'invalid publication date')
        path = REPO / REPORTS / (day + '.json')
        raw = path.read_bytes()
        report = json.loads(raw)
        validator.validate_report(path, report, u, public=True, compact=True)
        summary = validate_publication(report, raw, read_evidence(args.publication_evidence_dir, day), published)
        print(f'OK publication {day}: {summary["eligible_pairs"]}/50 eligible pairs')
    if not days:
        print('OK publication: no changed editions or index advances; archives retain structural validation')


if __name__ == '__main__':
    try:
        main()
    except PublicationError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError, subprocess.SubprocessError):
        print('ERROR: publication inputs or structural validation failed', file=sys.stderr)
        sys.exit(1)
