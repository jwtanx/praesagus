"""Offline publication boundaries; fictional admissions never certify real public use."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml
from ingest import forecast_scenario as scenario

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts/daily-market-brief'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load('publication_gate_test', SCRIPTS / 'publication_gate.py')
cases = load('publication_scenario_cases', ROOT / 'tests/test_forecast_scenario.py')
PUBLISHED = gate.publication_time('2026-10-21T22:01:00Z')


def fixed_rows():
    return [dict(zip(gate.IDENTITY, key)) for key in sorted(gate.FIXED)]


def packet():
    e, a = cases.make_case()
    e['source']['provider'] = 'moomoo-rest'
    cases.reseal(e, a)
    result = scenario.build_forecast_scenario(e, admission=a, issued_at=cases.ISSUE, report_cutoff=cases.CUTOFF)
    assert result['status'] == 'generated'
    bar = e['bars'][-1]
    row = dict(market='US', ticker='SPY', currency='USD', quote_status='observed', data_gaps=[],
               current_price_value=bar['close'], price_as_of=bar['close_at'],
               sources=[{'label': 'Fictional close', 'url': bar['source_url']}])
    row = scenario.apply_scenario_to_row(row, result)
    quote = dict(price=bar['close'], currency='USD', provider='moomoo-rest', source_field='close',
                 source_url=bar['source_url'], session_date=bar['session_date'], source_at=bar['close_at'],
                 observed_at=bar['retrieved_at'], ingested_at=bar['ingested_at'], known_at=bar['known_at'])
    rights = dict(schema_version=1, provider='moomoo-rest', authority='Fictional contract authority',
                  markets=['US'], fields=['quote.price', 'source.timestamps'],
                  uses=['public-website-display', 'redistribution'], evidence_url='https://example.invalid/rights',
                  verified_by='Fictional reviewer', verified_at='2026-10-01T00:00:00Z', expires_at='2026-11-01T00:00:00Z')
    item = dict(market='US', ticker='SPY', currency='USD', quote=quote, quote_rights=rights,
                evidence=e, admission=a, result_sha256=gate.digest(result))
    return row, item


def test_aggregate_35_boundary_is_only_fictional_eligibility_arithmetic():
    rows = fixed_rows()
    ids = sorted(gate.FIXED)
    assert gate.aggregate_pairs(rows, ids[:35], ids[:35]) == {
        'eligible_pairs': 35, 'denominator': 50, 'required_pairs': 35, 'passed': True}
    assert not gate.aggregate_pairs(rows, ids[:34], ids[:34])['passed']
    assert gate.aggregate_pairs(rows, ids[:35], ids[15:])['eligible_pairs'] == 20
    assert not gate.aggregate_pairs(rows, ids[:35], ids[15:])['passed']


@pytest.mark.parametrize('change', ['duplicate', 'drop', 'replace', 'currency'])
def test_fixed_denominator_and_identities_cannot_be_changed(change):
    rows = fixed_rows()
    if change == 'duplicate': rows[-1] = rows[0]
    elif change == 'drop': rows.pop()
    elif change == 'replace': rows[0]['ticker'] = 'UNKNOWN'
    else: rows[0]['currency'] = 'USD'
    with pytest.raises(gate.PublicationError): gate.aggregate_pairs(rows, [], [])


def test_existing_public_replay_accepts_only_exact_fictional_US_contract():
    row, item = packet()
    before = deepcopy((row, item))
    assert gate.row_eligibility(row, item, cases.CUTOFF, PUBLISHED)
    assert (row, item) == before


@pytest.mark.parametrize('change', ['private', 'rights', 'expired-rights', 'wrong-provider', 'wrong-market',
    'future-known', 'malformed-time', 'missing-zone', 'future-issue', 'future-cutoff', 'expired-target',
    'stale-reference', 'calendar-end', 'source', 'price', 'bool-price', 'prediction', 'result-hash',
    'identity', 'range', 'missing-evidence', 'false-flag', 'confidence', 'projection', 'price-time', 'source-link'])
def test_admission_price_time_and_exact_mapping_failures(change):
    row, item = packet()
    published = PUBLISHED
    cutoff = cases.CUTOFF
    if change == 'private': item['admission']['purpose'] = 'private_research_only'
    elif change == 'rights': item['quote_rights']['uses'] = ['private-research']
    elif change == 'expired-rights': item['quote_rights']['expires_at'] = '2026-10-21T22:00:00Z'
    elif change == 'wrong-provider': item['quote']['provider'] = 'other-provider'
    elif change == 'wrong-market': row['market'] = item['market'] = 'MY'
    elif change == 'future-known': item['quote']['known_at'] = '2026-10-21T23:00:00Z'
    elif change == 'malformed-time': item['quote']['source_at'] = 'yesterday'
    elif change == 'missing-zone': item['quote']['source_at'] = '2026-10-21T20:00:00'
    elif change == 'future-issue': row['forecast_as_of'] = '2026-10-22T22:00:00Z'
    elif change == 'future-cutoff': cutoff = '2026-10-22T22:00:00Z'
    elif change == 'expired-target': published = gate.publication_time('2026-10-22T20:00:00Z')
    elif change == 'stale-reference': item['quote']['session_date'] = '2026-10-20'
    elif change == 'calendar-end': published = gate.publication_time('2026-11-02T22:00:00Z')
    elif change == 'source': item['quote']['source_url'] = 'https://example.invalid/other'
    elif change == 'price': row['current_price_value'] += 1
    elif change == 'bool-price': row['current_price_value'] = True
    elif change == 'prediction': row['estimated_mid_case_value'] += 1
    elif change == 'result-hash': item['result_sha256'] = '0' * 64
    elif change == 'identity': item['ticker'] = 'QQQ'
    elif change == 'range': row['range_low_value'] = row['range_high_value'] + 1
    elif change == 'missing-evidence': item['evidence'] = None
    elif change == 'false-flag': item['quote_rights'] = {'approved': True}
    elif change == 'confidence': row['confidence'] = 'unavailable'
    elif change == 'projection': row['current_price_value'] = None
    elif change == 'source-link': row['sources'] = []
    else: row['price_as_of'] = '2026-10-20T20:00:00Z'
    assert not gate.row_eligibility(row, item, cutoff, published)


def test_actual_supported_US30_limit_cannot_meet_fixed_35():
    # Run the real existing rights contract for every fixed identity. No mocked eligibility.
    from ingest.daily_report_projection import validate_market_rights
    _, item = packet()
    accepted = set()
    for key in gate.FIXED:
        rights = deepcopy(item['quote_rights'])
        rights['markets'] = [key[0]]
        try:
            validate_market_rights(rights, PUBLISHED.isoformat(), markets=(key[0],),
                                   fields={'quote.price', 'source.timestamps'})
        except ValueError:
            continue
        accepted.add(key)
    assert len(accepted) == 30
    assert not gate.aggregate_pairs(fixed_rows(), accepted, gate.FIXED)['passed']


def test_report_hash_missing_evidence_and_duplicates_fail_closed():
    report = {'forecasts': fixed_rows(), 'metadata': {'as_of': cases.CUTOFF}}
    raw = json.dumps(report).encode()
    evidence = {'schema_version': 1, 'report_sha256': hashlib.sha256(raw).hexdigest(), 'rows': []}
    with pytest.raises(gate.PublicationError, match='0/50'): gate.validate_publication(report, raw, evidence, PUBLISHED)
    evidence['report_sha256'] = '0' * 64
    with pytest.raises(gate.PublicationError, match='exact report'): gate.validate_publication(report, raw, evidence, PUBLISHED)
    evidence['report_sha256'] = hashlib.sha256(raw).hexdigest()
    row, item = packet()
    evidence['rows'] = [item, item]
    with pytest.raises(gate.PublicationError, match='duplicate'): gate.validate_publication(report, raw, evidence, PUBLISHED)


@pytest.mark.parametrize('change', ['missing', 'symlink-file', 'symlink-dir', 'mode', 'oversize', 'duplicate', 'nan', 'fifo'])
def test_private_evidence_safe_io_and_sanitized_errors(tmp_path, change):
    folder = tmp_path / 'evidence'
    folder.mkdir(mode=0o700)
    file = folder / '2026-10-21.json'
    file.write_text('{"private-secret-marker":true}')
    file.chmod(0o600)
    if change == 'missing': file.unlink()
    elif change == 'symlink-file':
        saved = folder / 'original'; file.rename(saved); file.symlink_to(saved)
    elif change == 'symlink-dir':
        alias = tmp_path / 'alias'; alias.symlink_to(folder); folder = alias
    elif change == 'mode': file.chmod(0o644)
    elif change == 'oversize': file.write_bytes(b'x' * (gate.MAX_EVIDENCE + 1))
    elif change == 'duplicate': file.write_text('{"x":1,"x":2}')
    elif change == 'nan': file.write_text('{"x":NaN}')
    else: file.unlink(); os.mkfifo(file, 0o600)
    with pytest.raises(gate.PublicationError) as exc: gate.read_evidence(folder.resolve() if change != 'symlink-dir' else folder, '2026-10-21')
    assert 'private-secret-marker' not in str(exc.value)


def test_private_io_valid_missing_dir_and_date_traversal(tmp_path):
    folder = tmp_path / 'staging'; folder.mkdir(mode=0o700)
    file = folder / '2026-10-21.json'; file.write_text('{}'); file.chmod(0o600)
    assert gate.read_evidence(folder.resolve(), '2026-10-21') == {}
    for directory, day in [(None, '2026-10-21'), (folder, '../../secret')]:
        with pytest.raises(gate.PublicationError): gate.read_evidence(directory, day)


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


@pytest.fixture
def history(tmp_path):
    repo = tmp_path / 'repo'; repo.mkdir()
    git(repo, 'init', '-q'); git(repo, 'config', 'user.name', 'Fixture'); git(repo, 'config', 'user.email', 'fixture@example.invalid')
    folder = repo / gate.REPORTS; folder.mkdir(parents=True)
    (folder / '2026-10-01.json').write_text('{"expired_archive":true}')
    (folder / 'reports.json').write_text(json.dumps({'latest': '2026-10-01', 'reports': [{'date': '2026-10-01'}]}))
    git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'initial')
    return repo, folder, git(repo, 'rev-parse', 'HEAD')


def commit(repo):
    git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'fixture update')


def test_git_unrelated_and_index_label_change_preserve_expired_archives(history):
    repo, folder, base = history
    (repo / 'unrelated').write_text('change'); commit(repo)
    assert gate.changed_editions(repo, base) == []
    index = json.loads((folder / 'reports.json').read_text()); index['reports'][0]['label'] = 'New label'
    (folder / 'reports.json').write_text(json.dumps(index)); commit(repo)
    assert gate.changed_editions(repo, base) == []


def test_git_changed_unindexed_edition_and_index_advance_select_only_needed(history):
    repo, folder, base = history
    (folder / '2026-10-02.json').write_text('{}'); commit(repo)
    assert gate.changed_editions(repo, base) == ['2026-10-02']
    second = git(repo, 'rev-parse', 'HEAD')
    (folder / 'reports.json').write_text(json.dumps({'latest': '2026-10-02', 'reports': [{'date': '2026-10-01'}, {'date': '2026-10-02'}]}))
    commit(repo)
    assert gate.changed_editions(repo, second) == ['2026-10-02']
    (folder / '2026-10-01.json').write_text('{"edited_archive":true}'); commit(repo)
    assert gate.changed_editions(repo, second) == ['2026-10-01', '2026-10-02']


def test_initial_manual_missing_base_and_rename(history):
    repo, folder, base = history
    assert gate.changed_editions(repo, None) == ['2026-10-01']
    assert gate.changed_editions(repo, '0' * 40) == ['2026-10-01']
    with pytest.raises(gate.PublicationError): gate.changed_editions(repo, '1' * 40)
    (folder / '2026-10-01.json').rename(folder / '2026-10-02.json'); commit(repo)
    assert gate.changed_editions(repo, base) == ['2026-10-02']


def test_last_success_baseline_retains_failed_report_on_later_unrelated_push(history):
    repo, folder, last_success = history
    (folder / '2026-10-02.json').write_text('{"would_fail_publication":true}')
    commit(repo)
    failed_push = git(repo, 'rev-parse', 'HEAD')
    (repo / 'unrelated').write_text('later commit'); commit(repo)
    assert gate.changed_editions(repo, failed_push) == []
    assert gate.changed_editions(repo, last_success) == ['2026-10-02']


def test_changed_snapshot_companion_and_universe_select_publication(history):
    repo, folder, base = history
    snapshots = folder / 'market-snapshots'; snapshots.mkdir()
    (snapshots / '2026-10-01.json').write_text('{}'); commit(repo)
    assert gate.changed_editions(repo, base) == ['2026-10-01']
    previous = git(repo, 'rev-parse', 'HEAD')
    (folder / 'watchlist-universe-five.json').write_text('{}'); commit(repo)
    assert gate.changed_editions(repo, previous) == ['2026-10-01']


def test_event_base_and_workflows_use_event_and_actual_cutoff(history):
    repo, _, base = history
    assert gate.event_base(repo, 'push', {'before': base}) == base
    assert gate.event_base(repo, 'pull_request', {'pull_request': {'base': {'sha': base}}}) == base
    assert gate.event_base(repo, 'workflow_dispatch', {}) is None
    with pytest.raises(gate.PublicationError): gate.event_base(repo, 'schedule', {})
    for name in ['ci.yml', 'pages.yml']:
        text = (ROOT / '.github/workflows' / name).read_text()
        workflow = yaml.safe_load(text)
        steps = next(iter(workflow['jobs'].values()))['steps']
        publication = next(s for s in steps if 'publication_gate.py' in s.get('run', ''))
        assert 'continue-on-error' not in publication and 'if' not in publication
        assert 'fetch-depth: 0' in text
        assert 'publication_gate.py --github-event' in text
        assert 'date -u +%Y-%m-%dT%H:%M:%SZ' in text
        assert '--publication-evidence-dir "$PUBLICATION_EVIDENCE_DIR"' in text
        assert text.index('publication_gate.py') > text.index('validate_report_json.py')
        if name == 'pages.yml': assert text.index('publication_gate.py') < text.index('actions/upload-pages-artifact')
    pages = (ROOT / '.github/workflows/pages.yml').read_text()
    assert 'actions: read' in pages and "status: 'success'" in pages
    assert '--deployment-base "$PUBLICATION_DEPLOYMENT_BASE"' in pages
    assert pages.index('publication-baseline') < pages.index('publication_gate.py')


@pytest.mark.parametrize('value', ['2026-10-21', '2026-10-21T22:00:00', '2026-10-22T06:00:00+08:00', 'bad'])
def test_cutoff_requires_aware_actual_UTC(value):
    with pytest.raises(gate.PublicationError): gate.publication_time(value)


def test_cli_cannot_launder_expired_targets_using_old_metadata():
    result = subprocess.run([sys.executable, str(SCRIPTS / 'publication_gate.py'), '--date', '2026-10-21',
        '--publication-at', '2026-10-21T22:01:00Z'], capture_output=True, text=True)
    assert result.returncode == 1 and 'captured at this delivery' in result.stderr
    assert 'Traceback' not in result.stderr


def test_actual_archive_structural_validation_stays_separate_from_missing_publication_evidence():
    latest = json.loads((ROOT / gate.REPORTS / 'reports.json').read_text())['latest']
    result = subprocess.run([sys.executable, str(SCRIPTS / 'publication_gate.py'), '--date', latest,
        '--publication-at', datetime.now(timezone.utc).isoformat()], capture_output=True, text=True)
    assert result.returncode == 1 and 'publication evidence directory is required' in result.stderr
    assert 'Traceback' not in result.stderr


def test_main_uses_deployment_base_and_manual_revalidates_latest(monkeypatch, history):
    repo, _, base = history
    monkeypatch.setattr(gate, 'REPO', repo)
    event = repo / 'event.json'; event.write_text(json.dumps({'before': base}))
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event))
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'push')
    seen = []
    def selected(repository, comparison):
        seen.append(comparison)
        raise gate.PublicationError('selection reached')
    monkeypatch.setattr(gate, 'changed_editions', selected)
    args = ['--github-event', '--deployment-base', 'a' * 40,
            '--publication-at', datetime.now(timezone.utc).isoformat()]
    with pytest.raises(gate.PublicationError, match='selection reached'): gate.main(args)
    assert seen == ['a' * 40]
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'workflow_dispatch')
    with pytest.raises(gate.PublicationError, match='selection reached'): gate.main(args)
    assert seen[-1] is None
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'push')
    args[2] = ''
    with pytest.raises(gate.PublicationError, match='deployment base is required'): gate.main(args)
