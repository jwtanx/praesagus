"""Fictional complete directory pairs; no source admission or network access."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/stock-research'))
import collect
import config
import etf_directory as directory
import storage
from contracts import Batch, RESTError

spec = importlib.util.spec_from_file_location('directory_universe_cases', ROOT / 'tests/test_stock_research_universe.py')
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)
NOW = cases.NOW
STAMP = cases.STAMP


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*a, **kw):
        pytest.fail('network not authorized in directory fixtures')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def put(path, value):
    path.write_text(json.dumps(value, allow_nan=False))
    path.chmod(0o600)


def timestamp(ms):
    return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=ms)).isoformat()


def listing(symbol, *, kind='nasdaqlisted', etf='Y', test='N', alias=None):
    if kind == 'nasdaqlisted':
        return [symbol, 'Fictional fund', 'Q', test, 'N', '100', etf, 'N']
    return [symbol, 'Fictional fund', 'P', alias or symbol, etf, '100', test, symbol]


def make_pair(tmp_path, *, nasdaq=None, other=None, aliases=None, retrieved=None, known=None):
    private = tmp_path.resolve() / 'private'
    private.mkdir(mode=0o700)
    files = []
    for kind, rows in [('nasdaqlisted', nasdaq if nasdaq is not None else [listing('XLC')]),
                       ('otherlisted', other if other is not None else [listing('XLY', kind='otherlisted')])]:
        url, header = directory.FORMATS[kind]
        raw = ('|'.join(header) + '\n' + '\n'.join('|'.join(row) for row in rows)
               + '\nFile Creation Time: 1014202617:03' + '|' * (len(header) - 1) + '\n').encode()
        f = private / (kind + '.txt')
        f.write_bytes(raw)
        f.chmod(0o600)
        files.append(dict(kind=kind, path=str(f), source_url=url, bytes=len(raw),
                          sha256=hashlib.sha256(raw).hexdigest(), complete=True,
                          retrieved_at=timestamp(NOW - 1000 if retrieved is None else retrieved),
                          known_at=timestamp(NOW - 500 if known is None else known)))
    value = dict(schema_version=1, current_only=True, reviewed_by='Fictional reviewer',
                 files=files, symbol_aliases=aliases or [])
    path = private / 'manifest.json'
    put(path, value)
    return path, value


def rehash(path, value, index=0):
    item = value['files'][index]
    raw = Path(item['path']).read_bytes()
    item.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    put(path, value)


def test_complete_pair_lineage_full_enumeration_and_footer_timezone_unknown(tmp_path):
    path, value = make_pair(tmp_path, nasdaq=[listing('XLC'), listing('NO', etf='N'), listing('TEST', test='Y')])
    result = directory.load_pair(str(path), cutoff_ms=NOW)
    assert list(result['candidates']) == ['US.XLC', 'US.XLY']
    row = result['candidates']['US.XLC']
    assert row['row_number'] == 2 and row['known_at_ms'] == NOW - 500
    assert row['retrieved_at_ms'] == NOW - 1000 and row['source_sha256'] == value['files'][0]['sha256']
    assert row['discovery_origin'] == directory.POOL and result['admission'] is False
    assert result['sources']['nasdaqlisted']['footer'] == 'File Creation Time: 1014202617:03|||||||'
    assert result['sources']['nasdaqlisted']['footer_timezone'] is None
    assert result['source_authenticity'] == 'reviewed-declaration-not-independently-authenticated'


@pytest.mark.parametrize('change', ['missing', 'duplicate-kind', 'URL', 'incomplete', 'header', 'footer',
    'truncated', 'hash', 'bytes', 'empty', 'bad-row', 'flag', 'oversized', 'extra-manifest-key', 'naive-time'])
def test_pair_manifest_and_content_rejections_are_sanitized(tmp_path, change):
    path, value = make_pair(tmp_path)
    f = Path(value['files'][0]['path'])
    if change == 'missing':
        value['files'].pop()
    elif change == 'duplicate-kind':
        value['files'][1]['kind'] = 'nasdaqlisted'
    elif change == 'URL':
        value['files'][0]['source_url'] = 'https://example.invalid/PRIVATE_CANARY'
    elif change == 'incomplete':
        value['files'][0]['complete'] = False
    elif change == 'hash':
        value['files'][0]['sha256'] = 'a' * 64
    elif change == 'bytes':
        value['files'][0]['bytes'] += 1
    elif change == 'oversized':
        value['files'][0]['bytes'] = directory.MAX_FILE_BYTES + 1
    elif change == 'extra-manifest-key':
        value['PRIVATE_CANARY'] = True
    elif change == 'naive-time':
        value['files'][0]['known_at'] = '2026-10-15T00:00:00'
    else:
        raw = f.read_text()
        if change == 'header': raw = raw.replace('Symbol|', 'Wrong|', 1)
        if change == 'footer': raw = raw.replace('1014202617:03', '9932202699:99')
        if change == 'truncated': raw = '\n'.join(raw.splitlines()[:-1])
        if change == 'empty': raw = ''
        if change == 'bad-row': raw = raw.replace('Fictional fund|', 'Fictional|fund|')
        if change == 'flag': raw = raw.replace('|Y|N\n', '|UNKNOWN|N\n')
        f.write_text(raw)
        rehash(path, value)
    put(path, value)
    with pytest.raises(ValueError) as error:
        directory.load_pair(str(path), cutoff_ms=NOW)
    assert str(error.value) == 'etf-directory-invalid-input'


@pytest.mark.parametrize('retrieved,known,accepted', [
    (NOW - 86400000, NOW - 86400000, True),
    (NOW - 86400001, NOW - 1, False), (NOW + 1, NOW + 1, False),
    (NOW - 1000, NOW + 1, False), (NOW, NOW - 1, False)])
def test_freshness_actual_retrieval_and_known_time_edges(tmp_path, retrieved, known, accepted):
    path, _ = make_pair(tmp_path, retrieved=retrieved, known=known)
    if accepted:
        assert directory.load_pair(str(path), cutoff_ms=NOW)['known_at_ms'] == known
    else:
        with pytest.raises(ValueError): directory.load_pair(str(path), cutoff_ms=NOW)


@pytest.mark.parametrize('target', ['manifest', 'file', 'parent', 'permissions'])
def test_private_regular_file_no_symlink_components(tmp_path, target):
    path, value = make_pair(tmp_path)
    f = Path(value['files'][0]['path'])
    if target in ('manifest', 'file'):
        chosen = path if target == 'manifest' else f
        real = chosen.with_suffix('.real')
        chosen.rename(real)
        chosen.symlink_to(real)
    elif target == 'parent':
        alias = tmp_path / 'alias'
        alias.symlink_to(path.parent, target_is_directory=True)
        path = alias / path.name
    else:
        f.chmod(0o644)
    with pytest.raises(ValueError): directory.load_pair(str(path), cutoff_ms=NOW)


def test_reviewed_exact_punctuation_alias_and_conflicts_unknown(tmp_path):
    alias = dict(kind='nasdaqlisted', symbol='FUND.A', provider_code='US.FUND-A',
                 source_url='https://example.invalid/authored-alias', reviewed_by='Fictional reviewer')
    path, _ = make_pair(tmp_path, nasdaq=[listing('FUND.A'), listing('DUP'), listing('DUP'),
                                       listing('COLLIDE')],
                        other=[listing('OTHER', kind='otherlisted', alias='COLLIDE')], aliases=[alias])
    result = directory.load_pair(str(path), cutoff_ms=NOW)
    assert list(result['candidates']) == ['US.FUND-A']
    assert result['candidates']['US.FUND-A']['alias_review'] == alias
    assert len(result['rejections']) == 4 and all(r['classification'] == 'UNKNOWN' for r in result['rejections'])


def test_unreviewed_punctuation_cannot_guess_or_seed_and_alias_must_exist(tmp_path):
    path, value = make_pair(tmp_path, nasdaq=[listing('FUND.A')])
    result = directory.load_pair(str(path), cutoff_ms=NOW)
    assert 'US.FUND.A' not in result['candidates'] and result['rejections'][0]['reason'] == 'unreviewed-symbol'
    value['symbol_aliases'] = [dict(kind='nasdaqlisted', symbol='NOTLISTED', provider_code='US.XLC',
                                   source_url='https://example.invalid/alias', reviewed_by='Fictional')]
    put(path, value)
    with pytest.raises(ValueError): directory.load_pair(str(path), cutoff_ms=NOW)


def identity(security):
    return sum(ord(c) for c in security)


class Provider(cases.FakeProvider):
    def __init__(self, settings, *, fail_directory=False, stock_directory_overlap=False, directory_as_stock=False):
        super().__init__(settings)
        self.used = 0
        self.fail_directory = fail_directory
        self.overlap = stock_directory_overlap
        self.directory_as_stock = directory_as_stock
    def before(self):
        if self.used >= self.config.max_requests: raise RESTError('request-budget')
        self.used += 1
    def screen(self, **kw):
        self.before()
        batch = super().screen(**kw)
        if self.overlap:
            row = dict(batch.rows[0], code='US.XLC')
            return replace(batch, rows=(row,))
        return batch
    def basicinfo(self, codes):
        self.before()
        self.calls.append(('basicinfo', list(codes)))
        if self.fail_directory and any(c != 'US.DEMO' for c in codes): raise RESTError('upstream-failed')
        return Batch(tuple(dict(code=c, stock_id=identity(c), name='Fictional',
            stock_type='STOCK' if c == 'US.DEMO' or self.directory_as_stock else 'ETF', suspension=False)
            for c in codes), 'basic', 'success', None, 1)
    def snapshots(self, codes):
        self.before()
        return super().snapshots(codes)
    def history(self, security, **kw):
        self.before()
        return super().history(security, **kw)


def metadata(codes):
    result = dict(schema_version=1)
    for code in codes:
        for key, value in cases.metadata_for(code, identity(code)).items():
            if key == 'schema_version': continue
            if key == 'sector_crosswalk': result[key] = value
            else: result.setdefault(key, {}).update(value)
    return result


def settings_for(path, tmp_path, **kw):
    return config.CollectionConfig(state_parent=str(tmp_path / 'outputs'), etf_directory_manifest=str(path), **kw)


def run(settings, provider=None, *, offset=0, offline=False):
    return collect.run_collection(settings, provider=provider,
        metadata=metadata(['US.DEMO', 'US.XLC', 'US.XLY']), offline=offline,
        generated_at=STAMP + timedelta(seconds=offset), as_of_ms=NOW)


def load(folder):
    return json.loads((folder / 'state.json').read_text()), json.loads((folder / 'universe.json').read_text())


def test_full_enumeration_slice_resume_provenance_and_existing_selection(tmp_path):
    path, _ = make_pair(tmp_path)
    settings = settings_for(path, tmp_path, etf_directory_candidates_per_run=1, max_candidates=1)
    first_provider = Provider(settings)
    first = run(settings, first_provider)
    state, selected = load(first)
    assert state['pools']['etf_directory'] == ['US.XLC', 'US.XLY']
    assert all(state['pools'][p] == ['US.DEMO'] for p in ('winners', 'losers', 'volume'))
    assert state['etf_directory']['checkpoint']['completed'] == ['US.XLC']
    assert state['etf_directory']['unvisited_count'] == 1 and state['etf_directory']['pending_count'] == 0
    assert [row['code'] for row in selected['main']] == ['US.DEMO', 'US.XLC']
    assert next(r for r in selected['main'] if r['code'] == 'US.XLC')['selection_reasons'] == ['etf_directory']
    # Original stock work finishes before additional directory enrichment.
    assert first_provider.calls[5][0:2] == ('history', 'US.DEMO')
    assert first_provider.calls[6] == ('basicinfo', ['US.XLC'])
    before = (first / 'state.json').read_bytes()
    second = run(settings, Provider(settings), offset=1)
    latest, _ = load(second)
    assert latest['etf_directory']['checkpoint']['completed'] == ['US.XLC', 'US.XLY']
    assert latest['etf_directory']['unvisited_count'] == latest['etf_directory']['pending_count'] == 0
    assert latest['membership_first_seen_ms']['US.XLC'] == NOW
    assert (first / 'state.json').read_bytes() == before
    assert latest['etf_directory']['source']['candidates']['US.XLC']['known_at_ms'] == NOW - 500


def test_budget_failure_preserves_pending_resume_and_no_stock_displacement(tmp_path):
    path, _ = make_pair(tmp_path)
    settings = settings_for(path, tmp_path, provider=config.ProviderConfig(max_requests=6),
                            etf_directory_candidates_per_run=1)
    client = Provider(settings)
    first = run(settings, client)
    state, selected = load(first)
    assert client.used == 6 and all('US.XLC' not in str(call) for call in client.calls)
    assert state['etf_directory']['checkpoint']['pending'] == ['US.XLC']
    assert state['etf_directory']['pending_count'] == 1
    assert selected['coverage']['etf_directory']['enumerated_candidates'] == 2
    resumed = replace(settings, provider=config.ProviderConfig(max_requests=128))
    second = run(resumed, Provider(resumed), offset=1)
    state, _ = load(second)
    assert state['etf_directory']['checkpoint']['completed'] == ['US.XLC']
    assert state['etf_directory']['checkpoint']['pending'] == []


def test_mid_enrichment_interruption_is_not_skipped_on_resume(tmp_path):
    path, _ = make_pair(tmp_path)
    settings = settings_for(path, tmp_path, provider=config.ProviderConfig(max_requests=7),
                            etf_directory_candidates_per_run=1)
    first = run(settings, Provider(settings))
    state, _ = load(first)
    assert 'US.XLC' in state['identities'] and 'US.XLC' not in state['history_status']
    assert state['etf_directory']['checkpoint']['pending'] == ['US.XLC']
    resumed = replace(settings, provider=config.ProviderConfig(max_requests=128))
    client = Provider(resumed)
    state, _ = load(run(resumed, client, offset=1))
    assert state['etf_directory']['checkpoint']['completed'] == ['US.XLC']
    assert any(call[0:2] == ('history', 'US.XLC') for call in client.calls)


def test_directory_only_provider_stock_never_enters_company_or_speculative_pools(tmp_path):
    path, _ = make_pair(tmp_path)
    settings = settings_for(path, tmp_path)
    folder = run(settings, Provider(settings, directory_as_stock=True))
    state, selected = load(folder)
    assert [r['code'] for r in selected['main']] == ['US.DEMO']
    assert not selected['speculative']
    assert set(selected['coverage']['etf_directory']['nonfund_or_unverified']) == {'US.XLC', 'US.XLY'}
    assert 'US.XLC' not in state['pools']['volume']


def test_unregistered_directory_only_stock_cannot_leak_into_speculative_selection(tmp_path):
    path, _ = make_pair(tmp_path, nasdaq=[listing('PLAINFUNDA')],
                        other=[listing('PLAINFUNDB', kind='otherlisted')])
    settings = settings_for(path, tmp_path)
    class LowPrice(Provider):
        def history(self, security, **kw):
            batch = super().history(security, **kw)
            if security != 'US.DEMO':
                for row in batch.rows:
                    row.update(open=2., high=2.2, low=1.8, close=2., turnover=6000000.)
            return batch
    folder = collect.run_collection(settings, provider=LowPrice(settings, directory_as_stock=True),
        metadata=metadata(['US.DEMO', 'US.PLAINFUNDA', 'US.PLAINFUNDB']), generated_at=STAMP, as_of_ms=NOW)
    _, selected = load(folder)
    assert not selected['speculative']
    assert set(selected['coverage']['etf_directory']['nonfund_or_unverified']) == {'US.PLAINFUNDA', 'US.PLAINFUNDB'}


def test_source_changed_during_run_does_not_finalize_membership(tmp_path):
    path, value = make_pair(tmp_path)
    settings = settings_for(path, tmp_path)
    class Changed(Provider):
        def history(self, security, **kw):
            batch = super().history(security, **kw)
            value['reviewed_by'] = 'Changed fictional source review'
            put(path, value)
            return batch
    with pytest.raises(ValueError, match='etf-directory-source-changed'):
        run(settings, Changed(settings))
    assert not list(Path(settings.state_parent).glob('*/manifest.json'))


def test_overlap_retains_both_origins_without_duplicate_enrichment(tmp_path):
    path, _ = make_pair(tmp_path)
    settings = settings_for(path, tmp_path, etf_directory_candidates_per_run=1)
    client = Provider(settings, stock_directory_overlap=True)
    folder = run(settings, client)
    _, selected = load(folder)
    assert len([c for c in client.calls if c[0] == 'basicinfo']) == 1
    assert next(r for r in selected['main'] if r['code'] == 'US.XLC')['selection_reasons'] == [
        'etf_directory', 'losers', 'volume', 'winners']


def test_changed_pair_or_options_cannot_resume_old_generation_and_stale_offline_rejected(tmp_path):
    path, value = make_pair(tmp_path)
    settings = settings_for(path, tmp_path, etf_directory_candidates_per_run=1)
    first = run(settings, Provider(settings))
    old_policy = collect.compatibility(settings)
    changed = replace(settings, etf_directory_candidates_per_run=2)
    assert collect.compatibility(changed) != old_policy
    assert storage.latest_state(settings.state_parent, collect.compatibility(changed)) is None
    value['reviewed_by'] = 'Different fictional reviewer'
    put(path, value)
    assert collect.compatibility(settings) != old_policy
    assert storage.latest_state(settings.state_parent, collect.compatibility(settings)) is None
    assert load(first)[0]['etf_directory']['checkpoint']['completed'] == ['US.XLC']
    with pytest.raises(ValueError):
        collect.run_collection(settings, offline=True, as_of_ms=NOW + 86400001,
                               generated_at=STAMP + timedelta(days=2))


def test_offline_no_cache_enumerates_without_consuming_enrichment_cursor(tmp_path):
    path, _ = make_pair(tmp_path)
    settings = settings_for(path, tmp_path)
    state, selected = load(run(settings, offline=True))
    assert state['etf_directory']['checkpoint']['next_index'] == 0
    assert state['etf_directory']['checkpoint']['completed'] == []
    assert selected['main'] == [] and selected['coverage']['etf_directory']['unvisited_count'] == 2


def test_default_mode_compatibility_and_stock_calls_unchanged(tmp_path, monkeypatch):
    settings = config.CollectionConfig(state_parent=str(tmp_path / 'outputs'))
    expected = storage.sha(storage.canonical(dict(state_schema=1, history_schema=1, calendar='XNYS',
                                                adjustment=1, universe_policy=1)))
    monkeypatch.setattr(collect, 'load_pair', lambda *a, **kw: pytest.fail('optional importer called without option'))
    assert collect.compatibility(settings) == expected
    assert collect.compatibility(replace(settings, etf_directory_candidates_per_run=400)) == expected
    client = Provider(settings)
    state, selected = load(run(settings, client))
    assert len(client.calls) == 6 and 'etf_directory' not in state
    assert set(state['pools']) == {'winners', 'losers', 'volume'}
    assert [row['code'] for row in selected['main']] == ['US.DEMO']


@pytest.mark.parametrize('limit', [0, 401, True, '40'])
def test_new_config_limit_rejected(limit):
    with pytest.raises(ValueError): config.CollectionConfig(etf_directory_candidates_per_run=limit)


@pytest.mark.parametrize('change', ['container', 'missing-key', 'pending-type', 'pending-value',
    'completed-value', 'duplicate', 'cursor', 'limit-bool'])
def test_malformed_checkpoint_fails_cleanly_before_enrichment(tmp_path, change):
    path, _ = make_pair(tmp_path)
    source = directory.load_pair(str(path), cutoff_ms=NOW)
    _, checkpoint = collect.directory_slice(source, None, 1)
    if change == 'container': checkpoint = []
    elif change == 'missing-key': checkpoint.pop('binding')
    elif change == 'pending-type': checkpoint['pending'] = None
    elif change == 'pending-value': checkpoint['pending'] = [{}]
    elif change == 'completed-value': checkpoint['completed'] = ['US.NOTENUMERATED']
    elif change == 'duplicate': checkpoint['pending'] = ['US.XLC', 'US.XLC']
    elif change == 'cursor': checkpoint['next_index'] = True
    elif change == 'limit-bool': checkpoint['limit'] = True
    with pytest.raises(ValueError, match='etf-directory-checkpoint-invalid'):
        collect.directory_slice(source, checkpoint, 1)
