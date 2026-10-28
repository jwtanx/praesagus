#!/usr/bin/env python3
"""Run one explicitly reviewed, private PRSG-155 saved-model batch. Never collect or fit."""
import sys

# Check isolation before any filesystem-resolved standard-library imports.
if __name__ == '__main__' and not sys.flags.isolated:
    print('{"status":"blocked","reason_code":"isolated_python_required","message":"isolated Python required","action":"Run python3.11 -I -B with the absolute entry point and reviewed arguments."}')
    raise SystemExit(2)

import argparse
import csv
from datetime import date, datetime, timedelta
import hashlib
import io
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).resolve()
CODES = 'SPY AAPL V JNJ WMT XOM QQQ IWM JPM GS MSFT GOOGL NVDA TSM AVGO LLY ABT PG KO TSLA HD MCD COP SLB CAT GE UPS LIN FCX NEM'.split()
CODES = ['US.' + code for code in CODES]
HORIZONS = ['1d', '3d', '5d', 'next_week']
LIMITS = dict(work_seconds=58, cleanup_seconds=2, rss_bytes=536870912, threads=1, retries=0)
POLICY = dict(required_keys=120, qualified=0, actions=['NO TRADE'],
              unavailable_forecast_numbers='blank-with-reasons', partial_exit_code=4)
RUNTIME = {'scripts/stock-research/' + name + '.py' for name in
           ('run_reviewed_batch', 'data', 'storage', 'market_calendar', 'features', 'model', 'inference', 'ranking', 'export')}
BASIS_CODES = {'US.JPM', 'US.ABT', 'US.PG', 'US.CAT', 'US.GE', 'US.FCX'}
JSON_LIMIT, FILE_LIMIT, TOTAL_LIMIT = 2 * 1024**2, 32 * 1024**2, 128 * 1024**2
LABEL_CLASSES = {'historical-execution-label', 'historical-config-label', 'environment-label', 'third-party-path-label'}
NON_LABEL_FIELDS = {'prior_facts_path', 'accepted_history', 'accepted_receipt', 'financial_review', 'template_draft'}
ARCHIVE_MAP_SHA = 'da796d77da285776b5f1ab1b526ab6248381a44bbd85910f7a71b3cca3db8d4a'
HISTORICAL_ORIGINS = {
    'plans/2026-10-27/PRSG-152-remaining-us-model-source-cohorts.md': '8bf145720fa3813a0f1528f9a55afb2059c9a00fdfaee96b72509bac7c54beb8',
    'plans/2026-10-27/PRSG-152.harness.json': 'cf898883d0ce989ff3f6a27bd1989f60e50e040d27729a0c355e359da64bb953',
    'plans/2026-10-27/PRSG-153-full-us30-research-model-batch.md': '0a7313892f197e5fb3c3e33f6e539700046dffb345ac51829907f43c391af474',
}


class Blocked(ValueError):
    def __init__(self, reason, action='Obtain corrected, hash-bound inputs and a new reviewed release.'):
        super().__init__(reason)
        self.reason, self.action = reason, action


def need(condition, reason, action=None):
    if not condition:
        raise Blocked(reason, action) if action else Blocked(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def exact(value, expected):
    return canonical(value) == canonical(expected)


def keys(value, expected):
    need(type(value) is dict and set(value) == set(expected), 'input_schema_invalid')


def integer(value, low=0, high=2**63-1):
    need(type(value) is int and low <= value <= high, 'input_schema_invalid')
    return value


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def invalid(_):
        raise Blocked('nonfinite_json')
    need(len(raw) <= JSON_LIMIT, 'input_budget')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def path_check(value, *, directory=False, private=True):
    need(type(value) is str and value.startswith('/') and '..' not in Path(value).parts,
         'foreign_or_symlink_path')
    path = Path(value)
    need(str(path) == value and path == path.resolve(), 'foreign_or_symlink_path')
    for part in [path, *path.parents]:
        need(not part.is_symlink(), 'foreign_or_symlink_path')
    info = path.stat()
    need(info.st_uid == os.getuid() and (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)),
         'foreign_or_symlink_path')
    if private:
        need(stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600), 'private_permissions_required')
        if not directory:
            need(stat.S_IMODE(path.parent.stat().st_mode) == 0o700, 'private_permissions_required')
    return path


def narrow_root(value):
    path = path_check(value, directory=True)
    home = Path.home().resolve()
    need(len(path.parts) >= 4 and path != home and path not in home.parents and path != ROOT
         and not path.is_relative_to(ROOT) and path.name not in {'lead-state', 'private', 'store', 'moomoo-market-store'}
         and (not path.is_relative_to(home) or len(path.relative_to(home).parts) >= 3), 'broad_or_code_root_forbidden')
    need(not any(re.fullmatch(r'(?i)(?:\.ssh|\.aws|\.config|credentials?|secrets?|keychains?)', part)
                 for part in path.parts), 'credential_root_forbidden')
    return path


def read_file(path, *, private=True, limit=FILE_LIMIT):
    path = path_check(str(path), private=private)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_size <= limit,
             'input_budget')
        need(not private or stat.S_IMODE(info.st_mode) == 0o600, 'private_permissions_required')
        raw = stream.read(limit + 1)
        need(len(raw) == info.st_size and len(raw) <= limit, 'input_budget')
    return raw


def file_ref(ref):
    keys(ref, ('path', 'sha256', 'bytes'))
    need(type(ref['path']) is str and type(ref['sha256']) is str
         and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'input_schema_invalid')
    integer(ref['bytes'], high=FILE_LIMIT)


def clock_check(bundle, now):
    integer(now, 1)
    zone = ZoneInfo('Asia/Kuala_Lumpur')
    start = datetime.fromtimestamp(bundle['source_not_before_ms']/1000, zone).isoformat()
    end = datetime.fromtimestamp(bundle['issue_before_ms']/1000, zone).isoformat()
    need(bundle['source_not_before_ms'] <= now < bundle['issue_before_ms'], 'issue_window_closed',
         f'Use the explicitly reviewed window {start} through strictly before {end}; after expiry obtain a separately reviewed bundle and release.')
    need(bundle['source_not_before_ms'] <= bundle['minimum_known_ms'] <= bundle['as_of_ms'] <= now,
         'source_or_review_future')


def validate_shape(bundle):
    keys(bundle, ('schema_version', 'kind', 'purpose', 'read_roots', 'trusted_model_root', 'output_parent',
                  'inputs', 'model', 'runtime_files', 'data_files', 'calendar', 'expected_codes', 'horizons',
                  'reference_session', 'as_of_ms', 'minimum_known_ms', 'source_not_before_ms',
                  'issue_before_ms', 'limits', 'feature_variant', 'output_policy'))
    constants = dict(schema_version=1, kind='praesagus-reviewed-inference-bundle',
                     purpose='private-unvalidated-research', expected_codes=CODES, horizons=HORIZONS,
                     limits=LIMITS, feature_variant=dict(metadata=[], dated_metadata={}, benchmark=None),
                     output_policy=POLICY)
    need(all(exact(bundle[k], v) for k, v in constants.items()), 'dated_contract_mismatch')
    reference = bundle['reference_session']
    need(type(reference) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', reference) is not None
         and date.fromisoformat(reference).isoformat() == reference, 'input_schema_invalid')
    integer(bundle['source_not_before_ms'], 1)
    integer(bundle['issue_before_ms'], bundle['source_not_before_ms']+1)
    midnight = datetime.combine(date.fromisoformat(reference)+timedelta(days=1), datetime.min.time(),
                                tzinfo=ZoneInfo('America/New_York'))
    need(bundle['source_not_before_ms'] == int(midnight.timestamp()*1000), 'source_finality_mismatch')
    for key in ('as_of_ms', 'minimum_known_ms'):
        integer(bundle[key], 1)
    need(type(bundle['read_roots']) is list and 1 <= len(bundle['read_roots']) <= 128
         and all(type(x) is str for x in bundle['read_roots'])
         and len(set(bundle['read_roots'])) == len(bundle['read_roots']), 'input_schema_invalid')
    keys(bundle['inputs'], ('history_csv', 'receipt', 'instruments', 'source_review', 'model_compatibility_review'))
    keys(bundle['model'], ('folder', 'contract', 'manifest', 'artifact', 'child_fit_approval', 'parent_fit_approval'))
    keys(bundle['calendar'], ('name', 'version', 'start', 'end'))
    need(bundle['calendar']['name'] == 'XNYS' and all(type(v) is str for v in bundle['calendar'].values()),
         'input_schema_invalid')
    for key in ('start', 'end'):
        need(datetime.fromisoformat(bundle['calendar'][key]).date().isoformat() == bundle['calendar'][key],
             'input_schema_invalid')
    need(type(bundle['runtime_files']) is list and 1 <= len(bundle['runtime_files']) <= 256
         and type(bundle['data_files']) is list and len(bundle['data_files']) <= 2048, 'input_budget')


class Inventory:
    """Read only a finite, hash-bound inventory. Never follow an unlisted JSON path."""
    def __init__(self, bundle):
        self.roots = [narrow_root(value) for value in bundle['read_roots']]
        self.raw, self.documents, self.hashes = {}, {}, {}
        self.total = 0
        refs = [*bundle['inputs'].values(), *[v for k, v in bundle['model'].items() if k != 'folder'],
                *bundle['data_files']]
        need(len(refs) <= 2048 + 10, 'input_budget')
        self.aliases = {}
        for ref in refs:
            file_ref(ref)
            if ref['sha256'] != ARCHIVE_MAP_SHA:
                continue
            map_path = path_check(ref['path'])
            need(any(map_path.is_relative_to(root) for root in self.roots), 'foreign_or_symlink_path')
            raw = read_file(ref['path'], limit=JSON_LIMIT)
            need(digest(raw) == ARCHIVE_MAP_SHA and len(raw) == ref['bytes'], 'historical_archive_mismatch')
            mapping = decode(raw)
            entries = mapping.get('entries')
            need(type(entries) is list and len(entries) == 3, 'historical_archive_mismatch')
            for item in entries:
                original = item['original_path']
                relative = item['historical_input_path']
                need(relative in HISTORICAL_ORIGINS and original == str(ROOT / relative)
                     and item['original_sha256'] == HISTORICAL_ORIGINS[relative]
                     and item['snapshot']['sha256'] == HISTORICAL_ORIGINS[relative], 'historical_archive_mismatch')
                file_ref(item['snapshot'])
                need(original not in self.aliases, 'historical_archive_mismatch')
                self.aliases[original] = item['snapshot']
            need(set(self.aliases) == {str(ROOT / p) for p in HISTORICAL_ORIGINS}, 'historical_archive_mismatch')
        for ref in refs:
            file_ref(ref)
            resolved = self.aliases.get(ref['path'], ref)
            need(resolved['sha256'] == ref['sha256'] and resolved['bytes'] == ref['bytes'], 'historical_archive_mismatch')
            path = path_check(resolved['path'])
            need(any(path.is_relative_to(root) for root in self.roots), 'foreign_or_symlink_path')
            if str(path) in self.raw:
                need(self.hashes[str(path)] == ref['sha256'] and len(self.raw[str(path)]) == ref['bytes'],
                     'duplicate_reference_conflict')
                continue
            raw = read_file(path, limit=JSON_LIMIT if path.suffix == '.json' else FILE_LIMIT)
            need(len(raw) == ref['bytes'] and digest(raw) == ref['sha256'], 'input_hash_mismatch')
            self.total += len(raw)
            need(self.total <= TOTAL_LIMIT, 'input_budget')
            self.raw[str(path)], self.hashes[str(path)] = raw, digest(raw)
            if path.suffix == '.json':
                self.documents[str(path)] = decode(raw)
        for original, snapshot in self.aliases.items():
            need(snapshot['path'] in self.raw and self.hashes[snapshot['path']] == snapshot['sha256'], 'historical_archive_mismatch')
            self.raw[original], self.hashes[original] = self.raw[snapshot['path']], snapshot['sha256']
        self.labels = set()
        self.label_ledger_sha256 = None
        source = self.document(bundle['inputs']['source_review'])
        if 'provenance_path_labels_sha256' in source:
            ledger_sha = source['provenance_path_labels_sha256']
            ledger = self.by_hash(ledger_sha)
            keys(ledger, ('schema_version', 'kind', 'approved', 'known_at_ms', 'entries'))
            need(exact(ledger['schema_version'], 1) and ledger['kind'] == 'reviewed-provenance-path-labels'
                 and ledger['approved'] is True, 'path_label_ledger_unreviewed')
            integer(ledger['known_at_ms'], 1, bundle['as_of_ms'])
            need(type(ledger['entries']) is list and 1 <= len(ledger['entries']) <= 256, 'path_label_ledger_invalid')
            controls = {ref['sha256'] for ref in [*bundle['inputs'].values(),
                        *[v for k, v in bundle['model'].items() if k != 'folder']]}
            for index, entry in enumerate(ledger['entries']):
                keys(entry, ('document_sha256', 'pointer', 'value', 'classification', 'rationale'))
                need(entry['classification'] in LABEL_CLASSES and type(entry['rationale']) is str
                     and 0 < len(entry['rationale'].strip()) <= 4096 and type(entry['value']) is str
                     and entry['value'].startswith('/') and len(entry['value']) <= 8192
                     and entry['document_sha256'] not in controls and entry['document_sha256'] != ledger_sha,
                     'path_label_ledger_invalid')
                document = self.by_hash(entry['document_sha256'])
                parent, leaf, value = pointer_value(document, entry['pointer'])
                need(type(value) is str and value == entry['value'], 'path_label_binding_mismatch')
                need(leaf not in NON_LABEL_FIELDS and not (type(parent) is dict
                     and ({'path', 'sha256'} <= parent.keys() or leaf.endswith('_path')
                          and leaf[:-5]+'_sha256' in parent)), 'path_label_reference_forbidden')
                label = (entry['document_sha256'], entry['pointer'], entry['value'])
                need(label not in self.labels, 'path_label_duplicate')
                self.labels.add(label)
                # Validated declarations describe labels; they are not new references.
                self.labels.add((ledger_sha, '/entries/'+str(index)+'/value', entry['value']))
                self.labels.add((ledger_sha, '/entries/'+str(index)+'/pointer', entry['pointer']))
            self.label_ledger_sha256 = ledger_sha
        for path, doc in self.documents.items():
            self.closed(doc, self.hashes[path])

    def closed(self, value, document_sha=None, pointer=''):
        if type(value) is dict:
            if value.get('original_path') in self.aliases:
                need(value.get('original_sha256') == self.aliases[value['original_path']]['sha256'], 'historical_archive_mismatch')
            for name, item in value.items():
                if name in self.aliases:
                    need(item == self.aliases[name]['sha256'], 'historical_archive_mismatch')
                elif name.startswith('/') and type(item) is str and re.fullmatch('[0-9a-f]{64}', item):
                    need(name in self.raw and self.hashes[name] == item, 'unlisted_source_reference')
                if type(item) is str and item.startswith('/'):
                    paired = {'prior_facts_path': 'prior_facts_sha256', 'accepted_history': 'accepted_history_sha256',
                              'accepted_receipt': 'accepted_receipt_sha256', 'template_draft': 'template_wrapper_sha256',
                              'financial_review': 'financial_review_sha256'}.get(name)
                    if paired is None and name.endswith('_path'):
                        paired = name[:-5]+'_sha256'
                    if paired in value:
                        need(item in self.raw and self.hashes[item] == value[paired], 'paired_source_hash_mismatch')
            if {'path', 'sha256'} <= value.keys() and type(value['path']) is str and value['path'].startswith('/'):
                need(value['path'] in self.raw and self.hashes[value['path']] == value['sha256'], 'unlisted_source_reference')
                if 'bytes' in value:
                    integer(value['bytes'], high=FILE_LIMIT)
                    need(value['bytes'] == len(self.raw[value['path']]), 'input_hash_mismatch')
            for name, item in value.items():
                self.closed(item, document_sha, pointer+'/'+name.replace('~', '~0').replace('/', '~1'))
        elif type(value) is list:
            for index, item in enumerate(value):
                self.closed(item, document_sha, pointer+'/'+str(index))
        elif type(value) is str and value.startswith('/') and not value.startswith('/api/'):
            if (document_sha, pointer, value) in getattr(self, 'labels', set()):
                return
            # Directory labels may only be explicit roots or ancestors of listed files.
            p = Path(value)
            need(value in self.raw or any(p == Path(f).parent or p in Path(f).parents
                                         for f in self.raw) and any(p.is_relative_to(r) for r in self.roots),
                 'unlisted_source_reference')

    def document(self, ref):
        need(ref['path'] in self.documents, 'json_reference_required')
        return self.documents[ref['path']]

    def by_hash(self, value):
        need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'input_schema_invalid')
        matches = [p for p, h in self.hashes.items() if h == value and p in self.documents]
        need(len(matches) == 1, 'unlisted_source_reference')
        return self.documents[matches[0]]


def pointer_value(document, pointer):
    """Resolve one canonical RFC6901 pointer; never treat it as a filesystem path."""
    need(type(pointer) is str and pointer.startswith('/') and len(pointer) <= 8192, 'path_label_pointer_invalid')
    value, parent, leaf = document, None, None
    for token in pointer[1:].split('/'):
        need(re.search(r'~(?![01])', token) is None, 'path_label_pointer_invalid')
        leaf = token.replace('~1', '/').replace('~0', '~')
        parent = value
        if type(value) is list:
            need(re.fullmatch(r'0|[1-9][0-9]*', leaf) is not None and int(leaf) < len(value), 'path_label_pointer_invalid')
            value = value[int(leaf)]
        else:
            need(type(value) is dict and leaf in value, 'path_label_pointer_invalid')
            value = value[leaf]
    return parent, leaf, value


class BufferLoader(importlib.abc.Loader):
    """Compile exactly the verified bytes, bypassing caches and later source changes."""
    def __init__(self, path, raw):
        self.path, self.raw = path, raw

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.__file__ = self.path
        exec(compile(self.raw, self.path, 'exec'), module.__dict__)


class BufferFinder(importlib.abc.MetaPathFinder):
    def __init__(self, buffers):
        self.buffers = buffers

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.buffers:
            filename, raw = self.buffers[fullname]
            return importlib.util.spec_from_loader(fullname, BufferLoader(filename, raw), origin=filename)
        candidate = importlib.machinery.PathFinder.find_spec(fullname, path)
        origin = getattr(candidate, 'origin', None)
        if isinstance(origin, str) and origin not in ('built-in', 'frozen'):
            resolved = Path(origin).resolve()
            if resolved.is_relative_to(ROOT):
                raise ImportError('foreign_runtime_import')
        return None


def install_runtime(buffers):
    # Never use a caller's path or import a helper supplied in the bundle.
    sys.meta_path.insert(0, BufferFinder(buffers))


def runtime_check(bundle):
    paths, buffers = [], {}
    for ref in bundle['runtime_files']:
        keys(ref, ('repo_path', 'sha256', 'bytes'))
        name = ref['repo_path']
        need(type(name) is str and name in RUNTIME and '..' not in Path(name).parts, 'foreign_runtime_import')
        integer(ref['bytes'], high=FILE_LIMIT)
        need(type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'input_schema_invalid')
        raw = read_file(ROOT / name, private=False)
        need(len(raw) == ref['bytes'] and digest(raw) == ref['sha256'], 'runtime_hash_mismatch')
        paths.append(name)
        if name != 'scripts/stock-research/run_reviewed_batch.py':
            buffers[Path(name).stem] = (str(ROOT / name), raw)
    need(len(paths) == len(set(paths)) and set(paths) == RUNTIME, 'foreign_runtime_import')
    for name in ('data', 'storage', 'market_calendar', 'features', 'model', 'inference', 'ranking', 'export'):
        module = sys.modules.get(name)
        loader = getattr(module, '__loader__', None)
        need(module is None or isinstance(loader, BufferLoader) and loader.path == buffers[name][0]
             and loader.raw == buffers[name][1],
             'foreign_runtime_import')
    return buffers


def reviews_check(bundle, inventory):
    inputs, model = bundle['inputs'], bundle['model']
    source = inventory.document(inputs['source_review'])
    compat = inventory.document(inputs['model_compatibility_review'])
    hashes = {key: inputs[key]['sha256'] for key in ('history_csv', 'receipt', 'instruments')}
    mh = {key: ref['sha256'] for key, ref in model.items() if key != 'folder'}
    need(source.get('approved') is True and source.get('kind') == 'reviewed-source-admission'
         and source.get('reference_session') == bundle['reference_session'] and source.get('inputs_sha256') == hashes,
         'source_admission_missing')
    need(compat.get('approved') is True and compat.get('kind') == 'reviewed-model-compatibility'
         and compat.get('source_review_sha256') == inputs['source_review']['sha256']
         and compat.get('reference_session') == bundle['reference_session']
         and compat.get('inputs_sha256') == hashes and compat.get('model_sha256') == mh
         and compat.get('generation') == model['folder'], 'source_compatibility_unaccepted')
    for doc in (source, compat):
        need(all(exact(doc.get(k), bundle[k]) for k in ('reference_session', 'source_not_before_ms', 'issue_before_ms')),
             'review_date_binding_mismatch')
        integer(doc.get('known_at_ms'), bundle['source_not_before_ms'], bundle['minimum_known_ms'])
    for key in ('source_completed_at_ms', 'financial_review_known_ms', 'inference_purpose_review_known_ms',
                'lead_interface_admission_known_ms'):
        integer(source.get(key), bundle['source_not_before_ms'], bundle['minimum_known_ms'])
    need(exact(source.get('qualifications'), dict(native_currency=None, financial_currency='USD',
              provider_formula_certified=False, dividend_exclusion_certified=False, cash_added=False)),
         'source_qualifications_missing')
    basis = source.get('basis_evidence')
    need(type(basis) is dict and BASIS_CODES <= basis.keys(), 'basis_evidence_missing')
    for code in BASIS_CODES:
        item = basis[code]
        need(type(item) is dict and item.get('request_label_only') is True
             and all(item.get(k) is False for k in ('cash_added', 'provider_formula_certified', 'dividend_exclusion_certified')),
             'basis_evidence_missing')
    return source


def fit_check(bundle, inventory):
    model = bundle['model']
    root = narrow_root(bundle['trusted_model_root'])
    folder = path_check(model['folder'], directory=True)
    need(folder.parent == root and any(folder.is_relative_to(r) for r in inventory.roots), 'model_not_trusted')
    for key, name in (('contract', 'model_contract.json'), ('manifest', 'manifest.json'), ('artifact', 'model.joblib')):
        need(model[key]['path'] == str(folder / name), 'model_not_trusted')
    manifest = inventory.document(model['manifest'])
    need(manifest.get('kind') == 'stock-research-model' and exact(manifest.get('schema_version'), 1)
         and manifest.get('strong_model_accepted') is False, 'model_not_trusted')
    for name, entry in manifest['artifacts'].items():
        need(name == entry['path'] and Path(name).name == name, 'model_not_trusted')
        path = str(folder / name)
        need(path in inventory.raw and inventory.hashes[path] == entry['sha256']
             and type(entry['bytes']) is int and len(inventory.raw[path]) == entry['bytes'], 'model_or_fit_approval_mismatch')
    need({'model.joblib', 'model_contract.json', 'freeze.json'} <= manifest['artifacts'].keys(), 'model_not_trusted')
    child = inventory.document(model['child_fit_approval'])
    parent = inventory.document(model['parent_fit_approval'])
    need(child.get('generation') == parent.get('generation') == model['folder']
         and child.get('trusted_reload') is True and child.get('calibrated') is False
         and child.get('model_promotion') is False and parent.get('model_promotion') is False
         and parent.get('approved_research_artifact') is True
         and child.get('manifest_sha256') == model['manifest']['sha256']
         and child.get('model_contract_sha256') == model['contract']['sha256']
         and parent.get('fit_completed_receipt_sha256') == model['child_fit_approval']['sha256'],
         'model_or_fit_approval_mismatch')
    integer(child.get('completed_at_ms'), 1, bundle['as_of_ms'])
    integer(parent.get('model_known_not_before_ms'), child['completed_at_ms'], bundle['as_of_ms'])
    resource = inventory.by_hash(parent.get('supervisor_receipt_sha256'))
    need(resource.get('cleanup_verified') is True, 'cleanup_unverified')
    generated = datetime.fromisoformat(manifest['generated_at'])
    need(generated.tzinfo is not None and int(generated.timestamp()*1000) <= bundle['as_of_ms'], 'source_or_review_future')
    return parent['model_known_not_before_ms']


def release_check(bundle, bundle_sha, release, inventory, now):
    keys(release, ('schema_version', 'kind', 'approved', 'bundle_sha256', 'run_id', 'not_before_ms',
                   'expires_at_ms', 'resources_confirmed', 'exclusive_local_run_confirmed', 'review_reference'))
    need(exact(release['schema_version'], 1) and release['kind'] == 'praesagus-reviewed-inference-release'
         and release['approved'] is True and release['resources_confirmed'] is True
         and release['exclusive_local_run_confirmed'] is True and release['bundle_sha256'] == bundle_sha
         and type(release['run_id']) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}', release['run_id']),
         'release_missing_or_expired')
    start = integer(release['not_before_ms'], bundle['source_not_before_ms'])
    end = integer(release['expires_at_ms'], start+1, bundle['issue_before_ms'])
    need(start <= now < end and end-start <= 600000, 'release_missing_or_expired')
    file_ref(release['review_reference'])
    ref = release['review_reference']
    # This later release review cannot be part of the bundle's hash inventory:
    # it binds the already frozen bundle SHA (including it would create a cycle).
    path = path_check(ref['path'])
    need(any(path.is_relative_to(root) for root in inventory.roots), 'foreign_or_symlink_path')
    raw = read_file(path, limit=JSON_LIMIT)
    need(digest(raw) == ref['sha256'] and len(raw) == ref['bytes'], 'release_review_unlisted')
    review = decode(raw)
    need(review.get('approved') is True and review.get('bundle_sha256') == bundle_sha
         and review.get('run_id') == release['run_id']
         and all(exact(review.get(k), bundle[k]) for k in ('reference_session', 'source_not_before_ms', 'issue_before_ms')),
         'release_missing_or_expired')
    integer(review.get('known_at_ms'), bundle['source_not_before_ms'], now)


def preflight(bundle_path, expected_sha, release_path=None):
    raw = read_file(bundle_path, limit=JSON_LIMIT)
    need(type(expected_sha) is str and re.fullmatch('[0-9a-f]{64}', expected_sha)
         and digest(raw) == expected_sha, 'input_hash_mismatch')
    bundle = decode(raw)
    validate_shape(bundle)
    clock_check(bundle, now_ms())
    buffers = runtime_check(bundle)
    inventory = Inventory(bundle)
    inventory.runtime_buffers = buffers
    source = reviews_check(bundle, inventory)
    fit_check(bundle, inventory)
    output = narrow_root(bundle['output_parent'])
    need(not any(output == r or r.is_relative_to(output) for r in inventory.roots), 'output_overlaps_inputs')
    release = None
    if release_path:
        release = decode(read_file(release_path, limit=JSON_LIMIT))
        release_check(bundle, expected_sha, release, inventory, now_ms())
    return bundle, inventory, source, release


def now_ms():
    return int(time.time()*1000)


def calendar_and_history(bundle, inventory, *, csv_path=None):
    # No repository imports until the complete runtime inventory has passed.
    install_runtime(inventory.runtime_buffers)
    from data import read_csv, validate_window, valid_identity
    from market_calendar import MarketCalendar
    calendar = MarketCalendar(bundle['calendar']['start'], bundle['calendar']['end'], 'XNYS')
    need(calendar.version == bundle['calendar']['version'], 'calendar_version_mismatch')
    current_calendar(bundle, calendar, now_ms())
    inputs = bundle['inputs']
    receipt = inventory.document(inputs['receipt'])
    need(receipt.get('source_admitted') is True and receipt.get('inference_admission') is True
         and all(receipt.get(k) is False for k in ('training_admission', 'public_admission', 'strong_model_promotion'))
         and receipt.get('reference') == bundle['reference_session'] and exact(receipt.get('rows_per_code'), 51)
         and receipt.get('source_revision_held_codes') == [], 'source_admission_missing')
    for key in ('financial_review_known_ms', 'inference_purpose_review_known_ms', 'lead_interface_admission_known_ms', 'source_completed_at_ms'):
        integer(receipt.get(key), bundle['source_not_before_ms'], bundle['minimum_known_ms'])
    need(receipt.get('native_currency_literal') is None
         and receipt.get('currency_interpretation') == 'scoped-financial-USD-not-vendor-literal', 'source_qualifications_missing')
    bindings = receipt.get('identity_bindings')
    need(type(bindings) is list and len(bindings) == 30 and {b['code'] for b in bindings} == set(CODES), 'typed_identity_mismatch')
    ids = {}
    for item in bindings:
        need(valid_identity(item.get('stock_id')), 'typed_identity_mismatch')
        integer(item.get('known_at_ms'), bundle['source_not_before_ms'], bundle['minimum_known_ms'])
        integer(item.get('retrieved_at_ms'), item['known_at_ms'], bundle['minimum_known_ms'])
        ids[item['code']] = item['stock_id']
    instruments = inventory.document(inputs['instruments'])
    need(type(instruments) is list and [x['code'] for x in instruments] == CODES, 'typed_identity_mismatch')
    for item in instruments:
        need(type(item.get('stock_id')) is type(ids[item['code']]) and item['stock_id'] == ids[item['code']], 'typed_identity_mismatch')
        integer(item.get('metadata_known_at_ms'), bundle['source_not_before_ms'], bundle['minimum_known_ms'])
    contract = inventory.document(bundle['model']['contract'])
    trained = contract.get('provenance', {}).get('inputs', [])
    need(len(trained) == 1, 'model_or_fit_approval_mismatch')
    trained_ids = {b['code']: b['stock_id'] for b in trained[0].get('identity_bindings', [])}
    need(set(trained_ids) == set(CODES) and all(type(ids[c]) is type(trained_ids[c]) and ids[c] == trained_ids[c] for c in CODES),
         'typed_identity_mismatch')
    raw_rows = list(csv.DictReader(io.StringIO(inventory.raw[inputs['history_csv']['path']].decode())))
    need(len(raw_rows) == 1530 and len({(r['code'], r['session_date']) for r in raw_rows}) == 1530, 'required_sessions_missing')
    history = read_csv([csv_path or inputs['history_csv']['path']], receipt=receipt)
    dates = calendar.trailing_sessions(bundle['reference_session'], 51)
    need(len(dates) == 51, 'required_sessions_missing')
    training_hash = trained[0].get('file_sha256')
    training_files = [p for p, h in inventory.hashes.items() if h == training_hash and Path(p).suffix == '.csv']
    need(bool(training_files), 'training_source_inventory_missing',
         'Include the original training CSV bound by model provenance file_sha256 in the closed data_files inventory.')
    need(len(training_files) == 1, 'training_source_inventory_ambiguous',
         'Keep exactly one explicit original training CSV path for this model-bound file hash.')
    training_dates = {code: set() for code in CODES}
    for row in csv.DictReader(io.StringIO(inventory.raw[training_files[0]].decode())):
        need(row.get('code') in training_dates and type(row.get('session_date')) is str, 'training_source_inventory_invalid')
        need(date.fromisoformat(row['session_date']).isoformat() == row['session_date']
             and row['session_date'] <= bundle['reference_session']
             and row['session_date'] not in training_dates[row['code']], 'training_source_inventory_invalid')
        training_dates[row['code']].add(row['session_date'])
    need(all(training_dates.values()), 'training_source_inventory_invalid')
    shared = {code: [d for d in dates if d in training_dates[code]] for code in CODES}
    need(receipt.get('shared_training_dates_by_code') == shared, 'required_sessions_missing')
    for code in CODES:
        rows = [r for r in history.rows if r['code'] == code]
        need(sorted(r['session_date'] for r in rows) == dates, 'required_sessions_missing')
        validate_window(rows, dates, calendar, cutoff_ms=bundle['as_of_ms'], currency='USD')
        for row in rows:
            for key in ('known_at_ms', 'retrieved_at_ms', 'price_known_at_ms'):
                integer(row[key], bundle['source_not_before_ms'], bundle['minimum_known_ms'])
            integer(row['currency_known_at_ms'], 0, row['known_at_ms'])
    return calendar, history, instruments


def current_calendar(bundle, calendar, now):
    clock_check(bundle, now)
    closed = [d for d in calendar._sessions if calendar.close_ms(d) <= now]
    need(closed and closed[-1] == bundle['reference_session'], 'reference_no_longer_current')
    windows = calendar.windows(bundle['reference_session'])
    need(set(windows) == set(HORIZONS), 'calendar_window_invalid')
    first_open = min(calendar.open_ms(days[0]) for days in windows.values())
    need(bundle['issue_before_ms'] == first_open, 'first_open_deadline_mismatch')
    need(all(now < calendar.open_ms(days[0]) for days in windows.values()), 'issue_window_closed')
    return windows


def forecasts_check(payload, bundle, calendar, now):
    windows = current_calendar(bundle, calendar, now)
    rows = payload['forecasts']
    pairs = [(row['code'], row['horizon']) for row in rows]
    need(len(pairs) == 120 and len(set(pairs)) == 120
         and set(pairs) == {(c, h) for c in CODES for h in HORIZONS}, 'forecast_keys_invalid')
    need(exact(payload.get('validated_candidate_count'), 0), 'qualified_output_forbidden')
    available = 0
    for row in rows:
        win = row['window']
        days = windows[row['horizon']]
        need(row['origin'] == bundle['reference_session'] and win['sessions'] == days
             and win['first_open_ms'] == calendar.open_ms(days[0]) and win['last_close_ms'] == calendar.close_ms(days[-1])
             and win['started'] is False and bundle['as_of_ms'] == row['as_of_ms']
             and bundle['as_of_ms'] <= row['issued_at_ms'] <= now, 'forecast_window_invalid')
        need(row['decision']['action'] == 'NO TRADE' and row['validation']['qualified'] is False, 'qualified_output_forbidden')
        need(row.get('features', {}).get('instrument_class') is None
             and row.get('features', {}).get('signed_leverage') is None, 'historical_metadata_injected')
        need(row['status'] in ('available', 'unavailable'), 'forecast_numeric_invalid')
        if row['status'] == 'available':
            need(row['model'] is not None and row['baseline'] is not None, 'forecast_numeric_invalid')
            available += 1
        else:
            need(row['model'] is None and row['baseline'] is None and bool(row['reasons']), 'forecast_numeric_invalid')
    return dict(keys=120, available=available, withheld=120-available, qualified=0, actions=['NO TRADE'])


def write_exclusive(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def child_run(bundle_path, bundle_sha, release_path, run_dir):
    bundle, inventory, source, release = preflight(bundle_path, bundle_sha, release_path)
    need(release is not None and run_dir == Path(bundle['output_parent']) / release['run_id'], 'release_missing_or_expired')
    path_check(str(run_dir), directory=True)
    claim = decode(read_file(run_dir / 'claim.json', limit=JSON_LIMIT))
    need(claim == dict(run_id=release['run_id'], bundle_sha256=bundle_sha), 'run_id_consumed')
    # Existing readers/loaders reopen files. Stage the SAME verified bytes in the
    # exclusive private attempt so later changes to source paths cannot select a
    # different CSV or pickle between preflight and deserialization.
    staged = run_dir / 'verified-inputs'
    staged.mkdir(mode=0o700)
    csv_path = staged / 'history.csv'
    write_exclusive(csv_path, inventory.raw[bundle['inputs']['history_csv']['path']])
    models = staged / 'models'
    models.mkdir(mode=0o700)
    model_folder = models / 'accepted-model'
    model_folder.mkdir(mode=0o700)
    original = Path(bundle['model']['folder'])
    manifest = inventory.document(bundle['model']['manifest'])
    for name in ['manifest.json', *manifest['artifacts']]:
        write_exclusive(model_folder / name, inventory.raw[str(original / name)])
    calendar, history, instruments = calendar_and_history(bundle, inventory, csv_path=csv_path)
    from inference import load_existing_model, build_forecasts, write_forecast_payload
    from storage import Generation
    from export import forecast_row, csv_bytes, columns
    known = fit_check(bundle, inventory)
    model, contract, ref = load_existing_model(model_folder, trusted_root=models,
                                              expected_contract=inventory.document(bundle['model']['contract']))
    need(ref['model_sha256'] == bundle['model']['artifact']['sha256']
         and ref['artifact_manifest_sha256'] == bundle['model']['manifest']['sha256']
         and ref['contract_sha256'] == digest(canonical(contract)), 'model_or_fit_approval_mismatch')
    # Staging is a byte-preserving read mechanism, never a new fit/generation.
    ref['trusted_artifact_folder'] = bundle['model']['folder']
    ref['verified_snapshot_folder'] = str(model_folder)
    ref['snapshot_is_new_model_generation'] = False
    ref['artifact_known_at_ms'] = max(ref['artifact_known_at_ms'], known)
    issue = now_ms()
    current_calendar(bundle, calendar, issue)
    release_check(bundle, bundle_sha, release, inventory, issue)
    payload = build_forecasts(history, instruments, model=model, contract=contract, model_ref=ref,
                              calendar=calendar, issued_at_ms=issue, as_of_ms=bundle['as_of_ms'],
                              costs={}, dated_metadata={}, basis_evidence=source['basis_evidence'])
    counts = forecasts_check(payload, bundle, calendar, now_ms())
    # Conversion is the existing strict exporter: failures reject, never clip or repair.
    views = [forecast_row(row, False) for row in payload['forecasts']]
    generation = Generation(run_dir, kind='stock-research-reviewed-batch', as_of_ms=bundle['as_of_ms'])
    meta = write_forecast_payload(generation, payload)
    generation.write('forecasts.csv', csv_bytes(views, sorted(columns(views))))
    generation.json('coverage.json', counts | dict(research_only=True, promotion=False, training=False))
    path = generation.finish(**meta, offline=True, bundle_sha256=bundle_sha)
    hashes = {name: entry['sha256'] for name, entry in generation.manifest['artifacts'].items()}
    hashes['manifest.json'] = digest(read_file(path / 'manifest.json'))
    runtime_check(bundle)
    Inventory(bundle)
    forecasts_check(payload, bundle, calendar, now_ms())
    release_check(bundle, bundle_sha, release, inventory, now_ms())
    approval = dict(schema_version=1, run_id=release['run_id'], bundle_sha256=bundle_sha, generation=str(path),
                    issued_at_ms=issue, as_of_ms=bundle['as_of_ms'], reference_session=bundle['reference_session'],
                    counts=counts, artifact_hashes=hashes, approved_forecast_use=True)
    write_exclusive(run_dir / 'child-approved.json', canonical(approval))
    return 0


def process_snapshot(timeout=.5):
    result = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,pgid=,rss=,lstart='],
                            capture_output=True, text=True, timeout=timeout, check=True)
    table = {}
    for line in result.stdout.splitlines():
        parts = line.split(None, 4)
        need(len(parts) == 5, 'monitor_shape_invalid')
        pid, ppid, pgid, rss = map(int, parts[:4])
        need(pid > 0 and ppid >= 0 and pgid > 0 and rss >= 0, 'monitor_shape_invalid')
        table[pid] = (ppid, pgid, rss*1024, parts[4])
    return table


def process_scope(table, leader, owned):
    root_valid = leader not in table or leader not in owned or table[leader][3] == owned[leader]
    selected = {pid for pid, row in table.items() if owned.get(pid) == row[3]
                or root_valid and row[1] == leader and (pid not in owned or owned[pid] == row[3])}
    if root_valid:
        selected.add(leader)
    while True:
        extra = {pid for pid, row in table.items() if row[0] in selected
                 and (pid not in owned or owned[pid] == row[3])}
        if extra <= selected:
            break
        selected |= extra
    selected &= table.keys()
    for pid in selected:
        owned[pid] = table[pid][3]
    return selected


def group_state(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return None


def supervise(argv, *, limits=LIMITS):
    """Bound work and verify cleanup of observed groups/PID births, including detachment."""
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS',
                'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS', 'NUMBA_NUM_THREADS', 'LOKY_MAX_CPU_COUNT'):
        env[key] = '1'
    started = time.monotonic()
    proc = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    owned, groups, measurements = {}, {proc.pid: None}, []
    peak, reason, cleaned, max_gap = 0, None, False, 0.
    last_sample = started

    def observe(table):
        nonlocal reason
        if proc.pid in owned and proc.pid in table and owned[proc.pid] != table[proc.pid][3]:
            reason = reason or 'process_identity_changed'
        ids = process_scope(table, proc.pid, owned)
        for pid in ids:
            if table[pid][1] == pid:
                groups.setdefault(pid, table[pid][3])
        if proc.pid in table and groups[proc.pid] is None:
            groups[proc.pid] = table[proc.pid][3]
        return ids

    try:
        while True:
            table = process_snapshot()
            ids = observe(table)
            rss = sum(table[pid][2] for pid in ids)
            sampled = time.monotonic()
            max_gap = max(max_gap, sampled-last_sample)
            last_sample = sampled
            peak = max(peak, rss)
            measurements.append(dict(elapsed_seconds=sampled-started, rss_bytes=rss, processes=len(ids)))
            if reason:
                break
            if rss > limits['rss_bytes']:
                reason = 'resource_limit'
                break
            if sampled-started >= limits['work_seconds']:
                reason = 'execution_timeout'
                break
            if max_gap > 1:
                reason = 'monitor_gap'
                break
            if proc.poll() is not None:
                if observe(process_snapshot()):
                    reason = 'unexpected_descendants'
                break
            time.sleep(.025)
    except (Exception, KeyboardInterrupt):
        reason = reason or 'supervision_failed'
    finally:
        if not owned or peak <= 0:
            reason = reason or 'rss_unobserved'
        cleanup_deadline = min(started+limits['work_seconds']+limits['cleanup_seconds'],
                               time.monotonic()+limits['cleanup_seconds'])
        while time.monotonic() < cleanup_deadline:
            try:
                table = process_snapshot(timeout=min(.25, max(.001, cleanup_deadline-time.monotonic())))
                ids = observe(table)
                for group, birth in groups.items():
                    if group in table and birth is not None and table[group][3] != birth:
                        reason = reason or 'process_identity_changed'
                        continue
                    if birth is None and proc.poll() is not None and group_state(group) is not False:
                        reason = reason or 'cleanup_ownership_unknown'
                        continue
                    try:
                        os.killpg(group, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        reason = reason or 'cleanup_permission'
                for pid in ids:
                    if table[pid][3] != owned.get(pid):
                        continue
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        reason = reason or 'cleanup_permission'
                proc.poll()
                remaining = observe(process_snapshot(timeout=min(.25, max(.001, cleanup_deadline-time.monotonic()))))
                if proc.returncode is not None and not remaining and all(group_state(g) is False for g in groups):
                    cleaned = True
                    break
            except (Exception, KeyboardInterrupt):
                # Monitor outage leaves cleanup unverified. Stop already observed groups.
                for group in groups:
                    try:
                        os.killpg(group, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
                try:
                    proc.kill()
                    proc.wait(timeout=max(.001, cleanup_deadline-time.monotonic()))
                except (OSError, subprocess.SubprocessError):
                    pass
                reason = reason or 'cleanup_monitor_failed'
                break
            time.sleep(.02)
        if not cleaned:
            reason = reason or 'cleanup_unverified'
    elapsed = time.monotonic()-started
    return dict(returncode=proc.returncode, reason=reason, elapsed_seconds=elapsed, peak_group_rss_bytes=peak,
                cleanup_verified=cleaned, limits=limits, samples=len(measurements), observed_process_count=len(owned),
                owned_pid_births=owned, owned_groups=groups, measurements=measurements, max_sample_gap_seconds=max_gap,
                limitations='Sampled RSS, not a hard RSS/thread cap or absolute peak. PID start labels guard observed reuse; '
                            'descendants escaping before observation can be missed. Monitor gaps over1s and unobserved children reject.',
                approved=reason is None and proc.returncode == 0 and cleaned and peak > 0 and bool(owned)
                and max_gap <= 1 and elapsed <= limits['work_seconds']+limits['cleanup_seconds'])


def finalize(bundle, bundle_sha, release, inventory, run_dir, receipt):
    need(receipt['approved'] is True and receipt['cleanup_verified'] is True, receipt.get('reason') or 'cleanup_unverified')
    # Re-read inputs and release bytes in the caller before reaching this function.
    runtime_check(bundle)
    calendar, _, _ = calendar_and_history(bundle, inventory)
    approval_raw = read_file(run_dir / 'child-approved.json', limit=JSON_LIMIT)
    approval = decode(approval_raw)
    keys(approval, ('schema_version', 'run_id', 'bundle_sha256', 'generation', 'issued_at_ms', 'as_of_ms',
                    'reference_session', 'counts', 'artifact_hashes', 'approved_forecast_use'))
    need(exact(approval['schema_version'], 1) and approval['run_id'] == release['run_id']
         and approval['bundle_sha256'] == bundle_sha and approval['as_of_ms'] == bundle['as_of_ms']
         and approval['reference_session'] == bundle['reference_session'] and approval['approved_forecast_use'] is True,
         'child_approval_mismatch')
    generation = path_check(approval['generation'], directory=True)
    need(generation.parent == run_dir, 'foreign_or_symlink_path')
    need(set(approval['artifact_hashes']) == {'predictions.json', 'forecasts.csv', 'coverage.json', 'manifest.json'}, 'artifact_hash_mismatch')
    for name, expected in approval['artifact_hashes'].items():
        need(digest(read_file(generation / name)) == expected, 'artifact_hash_mismatch')
    payload = decode(read_file(generation / 'predictions.json', limit=JSON_LIMIT))
    counts = forecasts_check(payload, bundle, calendar, now_ms())
    need(approval['issued_at_ms'] == payload['issued_at_ms'] and exact(counts, approval['counts'])
         and decode(read_file(generation / 'coverage.json')) == counts | dict(research_only=True, promotion=False, training=False),
         'child_approval_mismatch')
    # Independently reconstruct exported bytes so an approval cannot attest a different CSV.
    from export import forecast_row, csv_bytes, columns
    views = [forecast_row(row, False) for row in payload['forecasts']]
    need(csv_bytes(views, sorted(columns(views))) == read_file(generation / 'forecasts.csv'), 'artifact_hash_mismatch')
    supervisor_raw = canonical(receipt)
    need(read_file(run_dir / 'supervisor-receipt.json') == supervisor_raw, 'supervisor_receipt_mismatch')
    release_check(bundle, bundle_sha, release, inventory, now_ms())
    current_calendar(bundle, calendar, now_ms())
    parent = dict(schema_version=1, run_id=release['run_id'], bundle_sha256=bundle_sha, generation=str(generation),
                  child_approval_sha256=digest(approval_raw), supervisor_receipt_sha256=digest(supervisor_raw),
                  artifact_hashes=approval['artifact_hashes'], approved_forecast_use=True)
    write_exclusive(run_dir / 'parent-approved.json', canonical(parent))
    # Consumers require the final receipt AND both approvals, never a lone CSV.
    current_calendar(bundle, calendar, now_ms())
    release_check(bundle, bundle_sha, release, inventory, now_ms())
    delivery = dict(status='complete' if counts['available'] == 120 else 'partial', generation=str(generation),
                    counts=counts, csv_sha256=approval['artifact_hashes']['forecasts.csv'],
                    child_approval_sha256=digest(approval_raw), parent_approval_sha256=digest(canonical(parent)),
                    bundle_sha256=bundle_sha, completed_at_ms=now_ms(), approved_forecast_use=True)
    write_exclusive(run_dir / 'delivery-receipt.json', canonical(delivery))
    # Late persistence leaves evidence but never a usable delivery approval.
    try:
        current_calendar(bundle, calendar, now_ms())
        release_check(bundle, bundle_sha, release, inventory, now_ms())
    except BaseException:
        (run_dir / 'delivery-receipt.json').unlink(missing_ok=True)
        (run_dir / 'parent-approved.json').unlink(missing_ok=True)
        raise
    return delivery, 0 if counts['available'] == 120 else 4


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--bundle-sha256', required=True)
    parser.add_argument('--release')
    parser.add_argument('--check-only', action='store_true')
    # Internal child executes this same reviewed entry point, never a path from the bundle.
    parser.add_argument('--internal-child', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    run_dir, stage = None, 2
    try:
        bundle, inventory, _, release = preflight(args.bundle, args.bundle_sha256, args.release)
        if args.internal_child:
            need(not args.check_only, 'input_schema_invalid')
            return child_run(args.bundle, args.bundle_sha256, args.release, Path(args.internal_child))
        if args.check_only:
            calendar_and_history(bundle, inventory)
            print(json.dumps(dict(status='inputs-checked' if release else 'inputs-checked-release-not-checked',
                                  model_loaded=False, worker_started=False)))
            return 0
        need(release is not None, 'release_missing_or_expired', 'Supply a new finite Lead inference release bound to this bundle SHA256.')
        run_dir = Path(bundle['output_parent']) / release['run_id']
        try:
            run_dir.mkdir(mode=0o700, exist_ok=False)
        except FileExistsError:
            raise Blocked('run_id_consumed', 'Preserve the prior attempt and request a new reviewed run ID.') from None
        write_exclusive(run_dir / 'claim.json', canonical(dict(run_id=release['run_id'], bundle_sha256=args.bundle_sha256)))
        stage = 3
        command = [sys.executable, '-I', '-B', str(SCRIPT), '--bundle', args.bundle, '--bundle-sha256', args.bundle_sha256,
                   '--release', args.release, '--internal-child', str(run_dir)]
        receipt = supervise(command)
        # Persist failures too; they never authorize consuming any child artifacts.
        write_exclusive(run_dir / 'supervisor-receipt.json', canonical(receipt))
        if not receipt['approved']:
            raise Blocked(receipt['reason'] or 'worker_failed')
        checked, inv, _, current_release = preflight(args.bundle, args.bundle_sha256, args.release)
        need(exact(current_release, release) and exact(checked, bundle), 'input_hash_mismatch')
        delivery, status = finalize(bundle, args.bundle_sha256, release, inv, run_dir, receipt)
        print(json.dumps(delivery))
        return status
    except (Blocked, OSError, ValueError, TypeError, KeyError, IndexError, OverflowError, ImportError, subprocess.SubprocessError) as error:
        reason = error.reason if isinstance(error, Blocked) else 'runtime_dependency_unavailable' if isinstance(error, ImportError) else 'invalid_or_missing_input'
        action = error.action if isinstance(error, Blocked) else 'Use the reviewed Python environment with matching dependencies.' if isinstance(error, ImportError) else 'Check explicit private file paths, permissions, schema and reviewed hashes.'
        report = dict(status='blocked' if stage == 2 else 'failed', reason_code=reason, message=reason.replace('_', ' '), action=action)
        if run_dir is not None and run_dir.exists():
            # A failed attempt cannot leave an approved parent/delivery behind.
            for name in ('parent-approved.json', 'delivery-receipt.json'):
                (run_dir / name).unlink(missing_ok=True)
            try:
                write_exclusive(run_dir / 'failure.json', canonical(report))
            except OSError:
                pass
        print(json.dumps(report))
        return stage


if __name__ == '__main__':
    raise SystemExit(main())
