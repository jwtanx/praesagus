"""Reviewed local official-directory pair: candidate discovery, never admission."""
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[2]
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_FILE_ROWS = 20000
MAX_AGE = timedelta(hours=24)
POOL = 'etf_directory'
FORMATS = {
    'nasdaqlisted': ('https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt',
        ('Symbol', 'Security Name', 'Market Category', 'Test Issue', 'Financial Status',
         'Round Lot Size', 'ETF', 'NextShares')),
    'otherlisted': ('https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt',
        ('ACT Symbol', 'Security Name', 'Exchange', 'CQS Symbol', 'ETF',
         'Round Lot Size', 'Test Issue', 'NASDAQ Symbol')),
}


def need(value, reason='invalid'):
    if not value:
        raise ValueError('etf-directory-' + reason)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def private_bytes(value, maximum):
    """Walk private input components without following symlinks; bounded regular file."""
    path = Path(value)
    need(path.is_absolute() and not path.is_relative_to(ROOT)
         and not any(part in ('.', '..') for part in path.parts)
         and not any(part.lower() in {'public', 'www', 'htdocs', 'artifacts', 'dist'} for part in path.parts)
         and not any((ancestor / '.git').exists() for ancestor in path.parents), 'private-path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parent.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        parent = os.fstat(fd)
        need(parent.st_uid == os.getuid() and stat.S_IMODE(parent.st_mode) == 0o700, 'private-path')
        child = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(child, 'rb') as stream:
            info = os.fstat(stream.fileno())
            need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                 and stat.S_IMODE(info.st_mode) in (0o400, 0o600)
                 and 0 < info.st_size <= maximum, 'file-budget-or-permission')
            result = stream.read(maximum + 1)
            need(0 < len(result) <= maximum, 'file-budget')
            return result
    finally:
        os.close(fd)


def pairs(values):
    result = {}
    for key, value in values:
        need(key not in result, 'duplicate-json-key')
        result[key] = value
    return result


def stamp(value):
    need(isinstance(value, str) and len(value) <= 64, 'time')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(parsed.tzinfo is not None and parsed.utcoffset() is not None, 'time')
    return parsed.astimezone(timezone.utc)


def millis(value):
    delta = value - datetime(1970, 1, 1, tzinfo=timezone.utc)
    micros = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
    return (micros + 999) // 1000


def _load(value, cutoff_ms):
    manifest_raw = private_bytes(value, MAX_MANIFEST_BYTES)
    manifest = json.loads(manifest_raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: need(False, 'json'))
    need(isinstance(manifest, dict) and set(manifest) == {
        'schema_version', 'current_only', 'reviewed_by', 'files', 'symbol_aliases'}, 'manifest')
    need(type(manifest['schema_version']) is int and manifest['schema_version'] == 1
         and manifest['current_only'] is True and isinstance(manifest['reviewed_by'], str)
         and 0 < len(manifest['reviewed_by']) <= 128, 'manifest')
    files = manifest['files']
    need(isinstance(files, list) and len(files) == 2
         and all(isinstance(item, dict) for item in files)
         and {item.get('kind') for item in files} == set(FORMATS), 'complete-pair')
    aliases = manifest['symbol_aliases']
    need(isinstance(aliases, list) and len(aliases) <= 5000, 'aliases')
    mappings = {}
    for item in aliases:
        need(isinstance(item, dict) and set(item) == {
            'kind', 'symbol', 'provider_code', 'source_url', 'reviewed_by'}, 'alias')
        need(item['kind'] in FORMATS and isinstance(item['symbol'], str)
             and 0 < len(item['symbol']) <= 64
             and isinstance(item['provider_code'], str)
             and re.fullmatch(r'US\.[A-Z][A-Z0-9.-]{0,63}', item['provider_code'])
             and isinstance(item['source_url'], str) and item['source_url'].startswith('https://')
             and isinstance(item['reviewed_by'], str) and 0 < len(item['reviewed_by']) <= 128, 'alias')
        key = (item['kind'], item['symbol'])
        need(key not in mappings, 'duplicate-alias')
        mappings[key] = item
    cutoff = None
    if cutoff_ms is not None:
        need(type(cutoff_ms) is int and cutoff_ms > 0, 'cutoff')
        cutoff = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=cutoff_ms)
    sources, rows, alias_index, used = {}, [], {}, set()
    for item in sorted(files, key=lambda value: value['kind']):
        need(set(item) == {'kind', 'path', 'source_url', 'bytes', 'sha256',
                           'retrieved_at', 'known_at', 'complete'}, 'file-manifest')
        kind = item['kind']
        url, header = FORMATS[kind]
        need(item['source_url'] == url and item['complete'] is True
             and type(item['bytes']) is int and 0 < item['bytes'] <= MAX_FILE_BYTES
             and isinstance(item['sha256'], str) and re.fullmatch('[a-f0-9]{64}', item['sha256']), 'source')
        retrieved, known = stamp(item['retrieved_at']), stamp(item['known_at'])
        need(retrieved <= known, 'time-order')
        if cutoff is not None:
            need(known <= cutoff and retrieved <= cutoff, 'future')
            need(cutoff - retrieved <= MAX_AGE, 'stale')
        content = private_bytes(item['path'], MAX_FILE_BYTES)
        need(len(content) == item['bytes'] and digest(content) == item['sha256'], 'hash-or-bytes')
        text = content.decode('utf-8')
        need(not any(ord(char) < 32 and char not in '\r\n' for char in text), 'control-character')
        lines = text.splitlines()
        need(3 <= len(lines) <= MAX_FILE_ROWS + 2 and tuple(lines[0].split('|')) == header, 'header-or-count')
        footer = lines[-1]
        parts = footer.split('|')
        # otherlisted is published with either seven or eight footer fields;
        # its header/data rows and the nasdaqlisted footer still require eight.
        footer_widths = (7, 8) if kind == 'otherlisted' else (8,)
        need(len(parts) in footer_widths and not any(parts[1:])
             and re.fullmatch(r'File Creation Time: [0-9]{10}:?[0-9]{2}', parts[0]), 'footer')
        # Validate the date/time syntax while deliberately leaving its timezone unknown.
        datetime.strptime(parts[0].split(': ', 1)[1].replace(':', ''), '%m%d%Y%H%M')
        sources[kind] = {key: item[key] for key in ('source_url', 'bytes', 'sha256', 'retrieved_at', 'known_at')}
        sources[kind].update(footer=footer, footer_timezone=None, rows=len(lines) - 2)
        for ordinal, fields in enumerate(csv.reader(io.StringIO('\n'.join(lines[1:-1])), delimiter='|', strict=True), 2):
            need(len(fields) == len(header) and all(len(field) <= 512 for field in fields), 'row')
            data = dict(zip(header, fields))
            symbol = fields[0]
            need(symbol and data['Security Name'] and data['ETF'] in ('Y', 'N')
                 and data['Test Issue'] in ('Y', 'N'), 'row')
            record = dict(kind=kind, row_number=ordinal, listed_symbol=symbol,
                          ETF=data['ETF'], test_issue=data['Test Issue'],
                          source_url=url, source_sha256=item['sha256'],
                          retrieved_at_ms=millis(retrieved), known_at_ms=millis(known))
            listing_aliases = {data[key] for key in ('Symbol', 'ACT Symbol', 'CQS Symbol', 'NASDAQ Symbol')
                               if data.get(key)}
            record['listing_aliases'] = sorted(listing_aliases)
            reviewed_alias = mappings.get((kind, symbol))
            if reviewed_alias:
                used.add((kind, symbol))
                record['provider_code'] = reviewed_alias['provider_code']
                record['alias_review'] = reviewed_alias
            elif re.fullmatch('[A-Z][A-Z0-9]{0,63}', symbol):
                record['provider_code'] = 'US.' + symbol
            else:
                record['provider_code'] = None
            index = len(rows)
            rows.append(record)
            for alias in listing_aliases:
                alias_index.setdefault(alias, set()).add(index)
    need(used == set(mappings), 'unmatched-alias')
    targets = {}
    for index, record in enumerate(rows):
        if record['provider_code']:
            targets.setdefault(record['provider_code'], set()).add(index)
    candidates, rejected = {}, []
    for index, record in enumerate(rows):
        if record['ETF'] != 'Y' or record['test_issue'] != 'N':
            continue
        security = record['provider_code']
        conflict = any(alias_index[alias] != {index} for alias in record['listing_aliases'])
        if security and security[3:] in alias_index:
            conflict = conflict or alias_index[security[3:]] != {index}
        if security is None or conflict or targets.get(security) != {index}:
            rejected.append(dict(record, classification='UNKNOWN', reason=(
                'unreviewed-symbol' if security is None else 'duplicate-or-ambiguous-listing')))
        else:
            candidates[security] = dict(record, discovery_origin=POOL, classification='candidate-only')
    binding = digest(canonical({'manifest_sha256': digest(manifest_raw), 'sources': sources}))
    return {'schema_version': 1, 'origin': POOL, 'current_only': True, 'binding_sha256': binding,
            'manifest_sha256': digest(manifest_raw), 'reviewed_by': manifest['reviewed_by'],
            'sources': sources, 'candidates': dict(sorted(candidates.items())), 'rejections': rejected,
            'known_at_ms': max(millis(stamp(item['known_at'])) for item in files),
            'source_authenticity': 'reviewed-declaration-not-independently-authenticated', 'admission': False}


def load_pair(value, *, cutoff_ms=None):
    try:
        return _load(value, cutoff_ms)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, csv.Error):
        # Uniform bounded error: no private path, input contents or native traceback text.
        raise ValueError('etf-directory-invalid-input') from None
