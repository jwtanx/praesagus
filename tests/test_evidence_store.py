"""Deterministic synthetic-only ledger replay; no providers, credentials or network."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from harness.evidence_store import EvidenceError, EvidenceStore

OBSERVED = '2026-10-01T22:00:00Z'
INGESTED = '2026-10-01T22:01:00Z'


def bar(**changes):
    record = dict(instrument='SYNTH-US', venue='TEST-US', currency='USD', exchange_timezone='America/New_York',
                  interval='1d', session='2026-10-01', session_type='regular', adjustment_basis='unadjusted',
                  bar_at='2026-10-01T09:30:00-04:00', completed_at='2026-10-01T16:00:00-04:00',
                  available_at='2026-10-01T20:01:00Z', observed_at=OBSERVED, completed=True,
                  open=100, high=105, low=98, close=103, volume=1000,
                  corporate_actions={}, source_version='fixture-v1')
    record.update(changes)
    return record


def news(**changes):
    content = 'Synthetic issuer release; no real company or forecast.'
    record = dict(item_id='synthetic-item-1', instruments=['SYNTH-US'], source_tier='primary',
                  url='https://example.org/synthetic-news', publication_raw='2026-10-01T19:00:00Z',
                  publication_timezone='UTC', publication_at='2026-10-01T19:00:00Z',
                  provider_available_at='2026-10-01T19:01:00Z', observed_at=OBSERVED,
                  event_cluster=None, content=content, content_hash=hashlib.sha256(content.encode()).hexdigest(),
                  source_version='fixture-v1')
    record.update(changes)
    if 'content' in changes and 'content_hash' not in changes:
        record['content_hash'] = hashlib.sha256(record['content'].encode()).hexdigest()
    return record


def batch(**changes):
    payload = dict(schema_version=1, origin='synthetic', provider='fixture-provider', run_id='fixture-run-1',
                   retrieved_at=OBSERVED, ingested_at=INGESTED, rights={'status': 'synthetic-only'},
                   run={'status': 'success', 'universe': ['SYNTH-US', 'SYNTH-MY'], 'session': '2026-10-01', 'error_reason': None},
                   bars=[bar()], news=[news()])
    payload.update(changes)
    return payload


def raw(payload):
    return json.dumps(payload, indent=2).encode()


@pytest.fixture
def store(tmp_path):
    return EvidenceStore(tmp_path / 'private-ledger')


def test_exact_raw_duplicate_and_private_storage(store):
    original = raw(batch()) + b'\n'
    first = store.ingest(original)
    assert first == dict(raw_hash=hashlib.sha256(original).hexdigest(), batches_added=1, runs_added=1,
                         bar_versions_added=1, news_versions_added=1, observations_added=2)
    assert store.raw(first['raw_hash']) == original
    repeat = store.ingest(original)
    assert all(value == 0 for key, value in repeat.items() if key != 'raw_hash')
    assert len(store.versions('bars', INGESTED)) == 1
    assert len(store.runs(INGESTED)) == 1
    assert store.database.stat().st_mode & 0o077 == 0
    assert store.raw_dir.stat().st_mode & 0o077 == 0
    assert (store.raw_dir / (first['raw_hash'] + '.json')).stat().st_mode & 0o777 == 0o400


def test_identical_payload_new_observation_and_revision(store):
    store.ingest(raw(batch()))
    later = batch(run_id='second', retrieved_at='2026-10-02T22:00:00Z', ingested_at='2026-10-02T22:01:00Z',
                  bars=[bar(observed_at='2026-10-02T22:00:00Z')], news=[news(observed_at='2026-10-02T22:00:00Z')])
    counts = store.ingest(raw(later))
    assert counts['bar_versions_added'] == counts['news_versions_added'] == 0
    assert counts['observations_added'] == 2
    assert len(store.versions('news', INGESTED)[0]['observations']) == 1
    assert len(store.versions('news')[0]['observations']) == 2
    later['run_id'] = 'third'
    later['bars'][0]['close'] = 104
    later['bars'][0]['corporate_actions'] = {'revision': 'synthetic correction'}
    later['news'][0] = news(content='Synthetic corrected release', source_version='fixture-v2', observed_at=later['retrieved_at'])
    counts = store.ingest(raw(later))
    assert counts['bar_versions_added'] == counts['news_versions_added'] == 1
    assert [row['revision'] for row in store.versions('bars')] == [1, 2]
    assert [row['record']['content'] for row in store.versions('news')] == [news()['content'], 'Synthetic corrected release']
    assert len(store.versions('news', INGESTED)) == 1


def test_us_my_daily_sessions_and_adjustment_identity(store):
    malaysian = bar(instrument='SYNTH-MY', venue='TEST-MY', currency='MYR', exchange_timezone='Asia/Kuala_Lumpur',
                    bar_at='2026-10-01T09:00:00+08:00', completed_at='2026-10-01T17:00:00+08:00',
                    available_at='2026-10-01T09:01:00Z')
    store.ingest(raw(batch(bars=[bar(), malaysian, bar(adjustment_basis='split-adjusted')])))
    assert len(store.versions('bars')) == 3
    assert store.versions('bars')[0]['record']['currency'] in {'USD', 'MYR'}


def test_backfilled_news_is_not_known_at_publication(store):
    late = news(publication_raw='2026-09-01T19:00:00Z', publication_at='2026-09-01T19:00:00Z', provider_available_at='2026-09-01T19:01:00Z')
    store.ingest(raw(batch(news=[late])))
    assert store.versions('news', '2026-09-02T22:00:00Z') == []
    assert store.versions('news', OBSERVED) == []  # Ingestion still later.
    historical = store.versions('news', '2026-09-02T22:00:00Z', historical=True)
    assert historical[0]['eligible'] is False
    assert historical[0]['view'] == 'historical-explanation'
    assert len(store.versions('news', INGESTED)) == 1


@pytest.mark.parametrize('changes,flag', [
    ({'publication_raw': None, 'publication_timezone': None, 'publication_at': None}, 'publication_unknown'),
    ({'provider_available_at': None}, 'availability_unknown'),
    ({'publication_raw': '2026-10-03T19:00:00Z', 'publication_at': '2026-10-03T19:00:00Z'}, 'publication_future'),
    ({'provider_available_at': '2026-10-03T19:00:00Z'}, 'availability_future'),
    ({'provider_available_at': '2026-10-01T18:00:00Z'}, 'publication_after_availability'),
    ({'publication_raw': '2026-09-01T19:00:00Z'}, 'publication_contradiction'),
])
def test_unknown_future_contradictory_news_retained_but_ineligible(store, changes, flag):
    record = news(**changes)
    store.ingest(raw(batch(news=[record])))
    assert store.versions('news', '2026-10-05T00:00:00Z') == []
    history = store.versions('news', historical=True)[0]
    assert flag in history['flags']
    assert history['record']['publication_at'] == record['publication_at']


@pytest.mark.parametrize('changes', [
    {'completed': False}, {'interval': 'snapshot'}, {'session_type': 'extended'},
    {'high': 99}, {'low': 104}, {'open': 0}, {'close': -1}, {'volume': -1}, {'high': float('nan')},
    {'volume': float('inf')}, {'open': True}, {'available_at': None}, {'completed_at': None},
    {'completed_at': '2026-10-03T20:00:00Z'}, {'available_at': '2026-10-03T20:01:00Z'},
    {'completed_at': '2026-10-01T19:00:00'}, {'bar_at': '2026-09-30T09:30:00-04:00'},
    {'instrument': 'UNDECLARED'}, {'exchange_timezone': 'invalid-zone'}, {'corporate_actions': None},
    {'source_version': None}, {'session': '2026-02-30'},
])
def test_invalid_bars_roll_back_entire_mixed_batch(store, changes):
    with pytest.raises(EvidenceError):
        store.ingest(raw(batch(bars=[bar(), bar(**changes)])))
    assert store.versions('bars', historical=True) == []
    assert store.runs() == []
    assert list(store.raw_dir.iterdir()) == []


@pytest.mark.parametrize('changes', [
    {'origin': 'live'}, {'schema_version': 2}, {'schema_version': True}, {'provider': ''},
    {'retrieved_at': '2026-10-01T22:00:00'}, {'ingested_at': '2026-09-30T22:00:00Z'},
    {'rights': {'status': 'licensed'}}, {'news': None}, {'bars': None},
])
def test_invalid_envelope(store, changes):
    with pytest.raises(EvidenceError):
        store.ingest(raw(batch(**changes)))


@pytest.mark.parametrize('changes', [
    {'publication_at': '2026-10-01T19:00:00'}, {'publication_raw': None},
    {'content_hash': 'bad'}, {'url': 'https://user:secret@example.org'}, {'url': 'javascript:alert(1)'},
    {'source_tier': 'invented'}, {'provider_available_at': 'not-time'}, {'instruments': ['OUTSIDE']},
    {'publication_timezone': 'bad-zone'}, {'observed_at': '2026-09-01T00:00:00Z'},
])
def test_invalid_news_rejected(store, changes):
    with pytest.raises(EvidenceError):
        store.ingest(raw(batch(news=[news(**changes)])))


def test_nullable_fields_must_be_declared(store):
    record = news()
    del record['provider_available_at']
    with pytest.raises(EvidenceError, match='explicit nullable'):
        store.ingest(raw(batch(news=[record])))


def test_collection_coverage_distinctions_and_run_revisions(store):
    assert store.runs() == []  # Unattempted, not successful-empty.
    for status in ('successful-empty', 'failed', 'partial', 'success'):
        run = {'status': status, 'session': '2026-10-01', 'universe': ['SYNTH-US', 'SYNTH-MY'],
               'error_reason': 'Synthetic bounded provider failure' if status in {'failed', 'partial'} else None}
        store.ingest(raw(batch(run=run, bars=[] if status in {'failed', 'successful-empty'} else [bar()], news=[])))
    runs = store.runs(INGESTED)
    assert [r['status'] for r in runs] == ['successful-empty', 'failed', 'partial', 'success']
    assert [r['revision'] for r in runs] == [1, 2, 3, 4]
    assert runs[0]['error_reason'] is None
    assert runs[1]['error_reason']
    assert store.runs('2026-09-01T00:00:00Z') == []


@pytest.mark.parametrize('status,records,error', [('failed', True, 'failure'), ('successful-empty', True, None),
                                                ('success', False, None), ('partial', False, None),
                                                ('failed', False, 'x' * 513), ('unknown', False, None)])
def test_invalid_run_contract(store, status, records, error):
    run = {'status': status, 'session': '2026-10-01', 'universe': ['SYNTH-US'], 'error_reason': error}
    with pytest.raises(EvidenceError):
        store.ingest(raw(batch(run=run, bars=[bar()] if records else [], news=[])))


@pytest.mark.parametrize('damage', ['missing', 'corrupted'])
def test_missing_or_corrupted_raw_detected_by_reads_and_reuse(store, damage):
    original = raw(batch())
    digest = store.ingest(original)['raw_hash']
    path = store.raw_dir / (digest + '.json')
    if damage == 'missing':
        path.unlink()
    else:
        path.chmod(0o600)
        path.write_bytes(b'corruption')
    with pytest.raises(EvidenceError):
        store.versions('bars')
    with pytest.raises(EvidenceError):
        store.runs()
    if damage == 'corrupted':
        with pytest.raises(EvidenceError):
            store.ingest(original)
    else:
        # Exact bytes can restore a missing artifact, without overwriting a file.
        assert store.ingest(original)['batches_added'] == 0
        assert store.raw(digest) == original


def test_database_lock_is_bounded_and_leaves_only_unreferenced_raw(store):
    with sqlite3.connect(store.database) as lock:
        lock.execute('BEGIN IMMEDIATE')
        store.lock_timeout = 0
        with pytest.raises(EvidenceError, match='locked'):
            store.ingest(raw(batch()))
        assert len(list(store.raw_dir.iterdir())) == 1
    assert store.runs() == []
    assert store.ingest(raw(batch()))['batches_added'] == 1


@pytest.mark.parametrize('version', [0, 2, 99])
def test_unknown_database_schema_is_preserved(tmp_path, version):
    root = tmp_path / 'ledger'
    root.mkdir(mode=0o700)
    database = root / 'evidence.sqlite3'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE untouched (value TEXT)')
        db.execute("INSERT INTO untouched VALUES ('preserve')")
        db.execute('PRAGMA user_version=' + str(version))
    database.chmod(0o600)
    with pytest.raises(EvidenceError, match='schema'):
        EvidenceStore(root)
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT value FROM untouched').fetchone()[0] == 'preserve'


def test_repository_and_public_permissions_rejected(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    with pytest.raises(EvidenceError, match='outside'):
        EvidenceStore(repo / 'artifacts' / 'must-not-create')
    public = tmp_path / 'public'
    public.mkdir(mode=0o755)
    public.chmod(0o755)
    with pytest.raises(EvidenceError, match='private'):
        EvidenceStore(public)


def test_raw_symlink_and_invalid_hash_rejected(store, tmp_path):
    digest = hashlib.sha256(raw(batch())).hexdigest()
    target = tmp_path / 'target'
    target.write_bytes(raw(batch()))
    (store.raw_dir / (digest + '.json')).symlink_to(target)
    with pytest.raises(EvidenceError, match='symlinks'):
        store.ingest(raw(batch()))
    with pytest.raises(EvidenceError, match='hash'):
        store.raw('../outside')


def test_sql_parameters_preserve_identity_text(store):
    payload = batch(provider="fixture'; DROP TABLE batches;--", run_id='synthetic SQL punctuation')
    store.ingest(raw(payload))
    assert store.runs()[0]['provider'] == payload['provider']


def test_bad_json_and_unsupported_query_rejected(store):
    for value in (b'[]', b'{"schema_version":1,"schema_version":1}', b'\xff', b'{', 'not bytes'):
        with pytest.raises(EvidenceError):
            store.ingest(value)
    with pytest.raises(EvidenceError):
        store.versions('quotes')
    with pytest.raises(EvidenceError):
        store.versions('news', '2026-10-01T00:00:00')


def test_cli_ingest_replay_and_rejection(tmp_path):
    root = tmp_path / 'private'
    payload = tmp_path / 'batch.json'
    payload.write_bytes(raw(batch()))
    cli = [sys.executable, str(Path(__file__).resolve().parents[1] / 'harness/evidence_store.py'), '--root', str(root)]
    first = subprocess.run(cli + ['ingest', str(payload)], capture_output=True, text=True)
    assert first.returncode == 0
    assert json.loads(first.stdout)['bar_versions_added'] == 1
    query = subprocess.run(cli + ['query', 'news', '--as-of', INGESTED], capture_output=True, text=True)
    assert query.returncode == 0
    assert json.loads(query.stdout)[0]['record']['item_id'] == 'synthetic-item-1'
    payload.write_bytes(raw(batch(origin='live')))
    rejected = subprocess.run(cli + ['ingest', str(payload)], capture_output=True, text=True)
    assert rejected.returncode == 2
    assert rejected.stdout == ''
    assert 'rejected' in rejected.stderr


def test_as_of_first_observation_does_not_leak_later_backdated_observation(store):
    store.ingest(raw(batch()))
    earlier_claim = '2026-10-01T21:00:00Z'
    store.ingest(raw(batch(run_id='late-replay', retrieved_at=earlier_claim, ingested_at='2026-10-03T00:00:00Z',
                          bars=[bar(observed_at=earlier_claim)], news=[news(observed_at=earlier_claim)])))
    version = store.versions('news', INGESTED)[0]
    assert version['first_observed_at'] == 1790892000.0  # Original 22:00 UTC observation.
    assert len(version['observations']) == 1


def test_changed_schema_rejected_on_existing_store(store):
    with sqlite3.connect(store.database) as db:
        db.execute('PRAGMA user_version=0')
    with pytest.raises(EvidenceError, match='schema'):
        store.runs()


def test_nonfinite_optional_metadata_rejected(store):
    data = raw(batch()).replace(b'"synthetic-only"', b'"synthetic-only", "invalid": 1e999')
    with pytest.raises(EvidenceError, match='nonfinite'):
        store.ingest(data)


def test_naive_raw_publication_contradiction_is_flagged(store):
    store.ingest(raw(batch(news=[news(publication_raw='2026-10-01T08:00:00', publication_timezone='America/New_York')])) )
    assert 'publication_contradiction' in store.versions('news', historical=True)[0]['flags']


def test_private_root_symlink_rejected(tmp_path):
    private = tmp_path / 'private'
    private.mkdir(mode=0o700)
    link = tmp_path / 'linked'
    link.symlink_to(private)
    with pytest.raises(EvidenceError, match='symlink'):
        EvidenceStore(link)


def test_transaction_failure_rolls_back_new_references_and_preserves_existing(store):
    original = raw(batch())
    store.ingest(original)
    before = store.versions('bars')
    with sqlite3.connect(store.database) as db:
        db.execute("CREATE TRIGGER synthetic_failure BEFORE INSERT ON news BEGIN SELECT RAISE(ABORT, 'synthetic storage failure'); END")
    changed = batch(run_id='must-rollback', bars=[bar(close=104)], news=[news(content='Synthetic new version')])
    with pytest.raises(EvidenceError, match='database operation failed'):
        store.ingest(raw(changed))
    assert store.versions('bars') == before
    assert len(store.runs()) == 1
    assert len(list(store.raw_dir.iterdir())) == 2  # Unreferenced immutable batch allowed.


def test_documented_synthetic_example_runs_without_network():
    documentation = (Path(__file__).resolve().parents[1] / 'harness/EVIDENCE_STORE.md').read_text()
    code = documentation.split('## Minimal synthetic US/MY example')[1].split('```python\n')[1].split('```')[0]
    exec(compile(code, 'synthetic documentation replay', 'exec'), {})



def test_schema_one_with_wrong_columns_rejected_on_open(tmp_path):
    root = tmp_path / 'schema-ledger'
    EvidenceStore(root)
    with sqlite3.connect(root / 'evidence.sqlite3') as db:
        db.execute('ALTER TABLE news ADD COLUMN unexpected TEXT')
    with pytest.raises(EvidenceError, match='columns'):
        EvidenceStore(root)


def test_overflow_integer_and_lone_surrogate_rejected(store):
    with pytest.raises(EvidenceError):
        store.ingest(raw(batch(bars=[bar(open=10 ** 400)])))
    data = raw(batch()).replace(b'fixture-provider', b'fixture-\\ud800')
    with pytest.raises(EvidenceError):
        store.ingest(data)



@pytest.mark.parametrize('kind', ['bars', 'news'])
def test_older_source_backfilled_after_newer_source_preserves_ingestion_order(store, kind):
    if kind == 'bars':
        newer = bar(source_version='source-v2', close=104, available_at='2026-10-01T21:00:00Z')
        older = bar(source_version='source-v1', close=103, observed_at='2026-10-02T22:00:00Z')
    else:
        newer = news(source_version='source-v2', content='Synthetic newer source correction',
                     publication_raw='2026-10-01T20:00:00Z', publication_at='2026-10-01T20:00:00Z',
                     provider_available_at='2026-10-01T20:01:00Z')
        older = news(source_version='source-v1', content='Synthetic older source release',
                     observed_at='2026-10-02T22:00:00Z')
    first_batch = batch(bars=[newer] if kind == 'bars' else [], news=[newer] if kind == 'news' else [])
    first_raw = raw(first_batch)
    first_hash = store.ingest(first_raw)['raw_hash']
    before = store.versions(kind, INGESTED)
    late_batch = batch(run_id='older-source-backfill', retrieved_at='2026-10-02T22:00:00Z',
                       ingested_at='2026-10-02T22:01:00Z',
                       bars=[older] if kind == 'bars' else [], news=[older] if kind == 'news' else [])
    late_raw = raw(late_batch)
    late_hash = store.ingest(late_raw)['raw_hash']
    assert store.versions(kind, INGESTED) == before  # No late version or observation leaks.
    assert [v['record']['source_version'] for v in before] == ['source-v2']
    assert len(store.versions(kind, late_batch['retrieved_at'])) == 1  # Not ingested yet.
    eligible = store.versions(kind, late_batch['ingested_at'])
    assert [v['revision'] for v in eligible] == [1, 2]
    assert [v['record']['source_version'] for v in eligible] == ['source-v2', 'source-v1']
    assert all(v['eligible'] for v in eligible)
    assert eligible[0]['identity'] == eligible[1]['identity']
    assert max(eligible, key=lambda v: v['revision'])['record']['source_version'] == 'source-v1'
    assert store.raw(first_hash) == first_raw
    assert store.raw(late_hash) == late_raw
    replay = store.ingest(late_raw)
    assert all(value == 0 for key, value in replay.items() if key != 'raw_hash')
    assert store.versions(kind, late_batch['ingested_at']) == eligible
