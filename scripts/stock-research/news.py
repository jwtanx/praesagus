"""Bounded supplied/cached news mechanics (schema 1); no live client or model.

Public API: validate_source_policy(policy, at_ms) -> permission receipt;
normalize_supplied_news(entries, source_receipt, policy) -> list[NewsRecord];
select_news_as_of(records, cutoff_ms, policy) -> records/rejected/coverage receipt;
The policy argument accepts one policy or a list of up to three: use ONE combined
call for all sources, never concatenate per-source selections. Event/target IDs
are externally reviewed canonical identities; hashes cannot establish causation.
collect_configured_news(policies, *, transport=None, clock_ms, cache=None,
mode='off') -> records/receipts/cache. Only explicit mode='collect' can call the
injected transport. NewsRequest carries endpoint, allowlisted conditional headers,
timeout_seconds=10 and max_bytes; NewsResponse carries status/body/headers/url.
Transport MUST enforce byte/deadline/redirect restrictions; fixtures cannot prove
that a live client does so. No default client, scheduler, authentication or fetch
of articles/enclosures exists. All DEFAULT_SOURCES are disabled.

NewsRecord has exactly RECORD_KEYS; integer millisecond times or explicit None.
article_id = digest([source_id, canonical_url]); content_hash = digest([headline,
permitted_text, text_scope, language]); text_version_id = digest([article_id,
content_hash, publication_at_ms, revision_known_at_ms]). digest is SHA256 of UTF8
JSON, sorted keys, compact separators, ASCII escaping. source_receipt_hash binds
supplied evidence; policy_hash binds the whole reviewed policy. Hashes do not
prove authenticity/rights. Source/relevance review remains an external gate.

Each relevance has exactly RELEVANCE_KEYS. security_id is a positive int OR a
positive decimal string, preserved and matched by type, never coerced. code is
US.<symbol>; entity/aspect/sentiment_scope/subject_identity are explicit strings.
relevance_kind is one of KINDS. status verified/unavailable; reason is None or a
bounded string; evidence_hash is SHA256; known_at_ms is int or None. One selected
record contains ONE relevance per event/typed instrument/entity/aspect/scope.
Manager, underlying and macro context never become fund tone; no scaling occurs.

All MS_FIELDS and relevance/policy known times must be available by cutoff.
Selection/rejection rows are each capped at 1000; expanded selected text is
capped at 4MiB and the complete serialized selection at 8MiB, without truncation.
Publication alone is not availability. first_seen/age_anchor are immutable across
revisions; 200 unchanged/304 never change record timestamps. Revised text keeps
original age, gains a new revision/ingestion time, and stays unavailable before
its own known time. revision_known_at_ms denotes the entire consumed evidence
envelope, not just text: changed relevance/event/rights/dedup/representative
annotations must advance it and ingestion_at_ms to actual annotation availability
and recompute text_version_id; preserve content/publication/first_seen/age when
text is unchanged. Same-time unequal envelopes conflict; never replace old bytes.
Feed parsing cannot infer entity relevance or cross-article
events: emits empty relevances and article-specific event IDs for later reviewed
supplied annotation. Selection therefore rejects unannotated feed text.

Collection cache is an explicit mutable dict: schema_version=1, records=list,
sources={source_id: state}, attempts=[{source_id, at_ms}]. Source state has exactly
STATE_KEYS. It is caller-owned, process/local only; no cross-host lock guarantee.
append_cache_generation(records, receipts, *, output_parent, generated_at=None)
returns an exclusive private generation path outside any Git checkout.
read_cache_generations(parent) -> validated records; read_collection_cache(parent)
-> reconstructed conditional/backoff cache. Only fixed metadata receipts persist;
raw response bytes, raw headers, exceptions, credentials and accounts never do.
The text/URL checks are not a general sensitive-data detector: credentials,
account/portfolio data and private exceptions are forbidden inputs to this API.
Cache reads reject more than 32 complete generations or 8MiB total bytes
(including manifests); no silent history pruning. Writes reserve 64KiB for the
manifest, and repeated identical text versions are deduplicated on bounded read.
"""
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit, unquote
import xml.etree.ElementTree as ET

from storage import Generation, ROOT as REPO_ROOT, StorageError

MAX_SOURCES = 3
MAX_RESPONSE = 2 * 1024 * 1024
MAX_ARTICLES = 1000
MAX_TEXT = 32768
MAX_TOTAL_TEXT = 4 * 1024 * 1024
MAX_CACHE = 8 * 1024 * 1024
MAX_SELECTED = 1000
MAX_GENERATIONS = 32  # Whole-parent bounded replay; overflow rejects, never drops history.
MS_FIELDS = ('publication_at_ms', 'first_seen_at_ms', 'retrieved_at_ms', 'revision_known_at_ms',
             'ingestion_at_ms', 'rights_known_at_ms', 'dedup_known_at_ms',
             'representative_known_at_ms', 'age_anchor_at_ms')
RELEVANCE_KEYS = {'code', 'security_id', 'target_entity_id', 'target_aspect', 'sentiment_scope',
                  'relevance_kind', 'subject_identity', 'status', 'reason', 'evidence_hash', 'known_at_ms'}
RECORD_KEYS = {'schema_version', 'article_id', 'canonical_url', 'source_id', 'source_url',
               'source_receipt_hash', 'policy_hash', 'content_hash', 'text_version_id', 'event_id',
               'dedup_version', 'dedup_evidence_hash', 'representative_evidence_hash', 'headline',
               'permitted_text', 'text_scope', 'language', 'publication_raw', 'publication_timezone',
               'relevances'} | set(MS_FIELDS)
KINDS = {'issuer_company', 'fund_product', 'manager_corporate', 'underlying_context', 'macro_context'}
DEFAULT_SOURCES = ({'source_id': 'sec', 'enabled': False}, {'source_id': 'nvidia-ir', 'enabled': False},
                   {'source_id': 'nasdaq', 'enabled': False})
SECRET = re.compile(r'authorization|password|passphrase|private.?key|account.?id|access.?token|api.?key|signature', re.I)
POLICY_KEYS = {'schema_version', 'source_id', 'enabled', 'endpoint', 'source_url', 'rights_status',
               'polling_status', 'known_at_ms', 'evidence_hash', 'text_scopes', 'poll_interval_ms',
               'permitted_min_interval_ms', 'max_age_ms'}
LIMITS = {'response_bytes': MAX_RESPONSE, 'articles': MAX_ARTICLES, 'article_text_bytes': MAX_TEXT,
          'total_text_bytes': MAX_TOTAL_TEXT, 'cache_bytes': MAX_CACHE}
STATE_KEYS = {'policy_hash', 'endpoint', 'etag', 'last_modified', 'body_hash', 'checked_at_ms',
              'next_allowed_at_ms', 'attempted_at_ms'}
RECEIPT_KEYS = STATE_KEYS | {'source_id', 'status', 'reason'}
REASONS = {'off', 'offline', 'policy-disabled-or-unknown', 'poll-not-due', 'backoff',
           'request-budget', 'transport-unavailable', 'transport-failure', 'http-error',
           'retry-after', 'not-modified', 'unchanged', 'collected', 'invalid-response',
           'response-budget', 'unsafe-xml', 'invalid-feed', 'article-budget',
           'article-text-budget', 'aggregate-text-budget', 'cache-artifact-budget',
           'invalid-original-time', 'news-time-order', 'invalid-response-clock', 'transport-timeout'}


class NewsError(ValueError):
    pass


@dataclass(frozen=True)
class NewsRequest:
    endpoint: str
    headers: tuple
    timeout_seconds: int = 10
    max_bytes: int = MAX_RESPONSE


@dataclass(frozen=True)
class NewsResponse:
    status: int
    body: bytes = b''
    headers: dict = field(default_factory=dict)
    url: str | None = None


def need(value, reason):
    if not value:
        raise NewsError(reason)


def encoded(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise NewsError('invalid-json-value') from None


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def text(value, limit=512, empty=False):
    return (isinstance(value, str) and (empty or bool(value))
            and len(value.encode('utf-8', errors='surrogatepass')) <= limit
            and not any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in value))


def stamp(value):
    return type(value) is int and 0 < value < 2**63


def hashed(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def url(value):
    if not text(value, 2048) or SECRET.search(unquote(value)):
        return False
    try:
        parts = urlsplit(value)
        return (parts.scheme == 'https' and bool(parts.hostname) and parts.username is None
                and parts.password is None and parts.port in (None, 443)
                and not parts.fragment and not parts.query and '\\' not in value
                and all(c.isascii() and (c.isalnum() or c in '.-') for c in parts.hostname))
    except ValueError:
        return False


def _member(value, choices):
    return isinstance(value, str) and value in choices


def _limits(policy):
    limits = policy.get('limits', {})
    need(isinstance(limits, dict) and set(limits) <= set(LIMITS), 'invalid-policy-limits')
    need(all(type(v) is int and 0 < v <= LIMITS[k] for k, v in limits.items()), 'invalid-policy-limits')
    return LIMITS | limits


def validate_source_policy(policy, at_ms):
    need(stamp(at_ms) and isinstance(policy, dict), 'invalid-source-policy')
    need(all(isinstance(k, str) and not SECRET.search(k) for k in policy), 'private-policy-field')
    need(set(policy) <= POLICY_KEYS | {'limits'} and len(encoded(policy)) <= 4096, 'invalid-source-policy')
    receipt = {'status': 'disabled', 'reason': 'policy-disabled-or-unknown', 'policy_hash': digest(policy)}
    if policy.get('enabled') is not True:
        return receipt
    need(set(policy) in (POLICY_KEYS, POLICY_KEYS | {'limits'})
         and type(policy['schema_version']) is int and policy['schema_version'] == 1, 'invalid-source-policy')
    need(text(policy['source_id']) and not SECRET.search(policy['source_id']) and re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', policy['source_id'])
         and url(policy['endpoint']) and url(policy['source_url']) and hashed(policy['evidence_hash']), 'invalid-source-policy')
    need(stamp(policy['known_at_ms']) and type(policy['max_age_ms']) is int
         and 0 < policy['max_age_ms'] < 2**62, 'invalid-policy-time')
    _limits(policy)
    if policy['known_at_ms'] > at_ms or policy['rights_status'] != 'verified' or policy['polling_status'] != 'verified':
        return receipt
    need(type(policy['poll_interval_ms']) is int and policy['poll_interval_ms'] in (60000, 300000), 'invalid-poll-interval')
    need(type(policy['permitted_min_interval_ms']) is int
         and 0 < policy['permitted_min_interval_ms'] <= policy['poll_interval_ms'], 'polling-not-permitted')
    scopes = policy['text_scopes']
    need(isinstance(scopes, list) and bool(scopes) and len(scopes) <= 2
         and all(_member(s, {'headline-only', 'full-permitted'}) for s in scopes)
         and len(set(scopes)) == len(scopes), 'invalid-text-rights')
    return receipt | {'status': 'permitted', 'reason': None}


def _validate_record(record):
    need(isinstance(record, dict) and set(record) == RECORD_KEYS, 'news-record-schema')
    need(type(record['schema_version']) is int and record['schema_version'] == 1, 'news-record-schema')
    need(url(record['canonical_url']) and url(record['source_url']), 'unsafe-source-url')
    for key in ('source_id', 'event_id', 'dedup_version', 'language'):
        need(text(record[key]), 'invalid-news-text')
    for key in ('headline', 'permitted_text'):
        need(text(record[key], MAX_TEXT, empty=key == 'permitted_text'), 'article-text-budget')
    need(len((record['headline'] + record['permitted_text']).encode()) <= MAX_TEXT, 'article-text-budget')
    need(_member(record['text_scope'], {'headline-only', 'full-permitted'}), 'invalid-text-scope')
    need(record['text_scope'] != 'headline-only' or record['permitted_text'] == '', 'headline-scope-mismatch')
    for key in MS_FIELDS:
        need(record[key] is None or stamp(record[key]), 'invalid-news-time')
    for key in ('publication_raw', 'publication_timezone'):
        need(record[key] is None or text(record[key]), 'invalid-original-time')
    if record['publication_raw'] is not None and record['publication_at_ms'] is not None:
        parsed, zone = _publication(record['publication_raw'])
        need(parsed == record['publication_at_ms'] and record['publication_timezone'] == zone, 'original-time-mismatch')
    for key in ('source_receipt_hash', 'policy_hash', 'content_hash', 'article_id', 'text_version_id',
                'dedup_evidence_hash', 'representative_evidence_hash'):
        need(hashed(record[key]), 'invalid-news-hash')
    need(record['article_id'] == digest([record['source_id'], record['canonical_url']]), 'article-id-mismatch')
    need(record['content_hash'] == digest([record[k] for k in ('headline', 'permitted_text', 'text_scope', 'language')]), 'content-hash-mismatch')
    need(record['text_version_id'] == digest([record['article_id'], record['content_hash'],
                                            record['publication_at_ms'], record['revision_known_at_ms']]), 'text-version-mismatch')
    if all(record[k] is not None for k in ('publication_at_ms', 'first_seen_at_ms', 'retrieved_at_ms',
                                          'revision_known_at_ms', 'ingestion_at_ms', 'age_anchor_at_ms')):
        need(record['publication_at_ms'] <= record['first_seen_at_ms'] <= record['retrieved_at_ms'] <= record['ingestion_at_ms']
             and record['first_seen_at_ms'] <= record['revision_known_at_ms'] <= record['ingestion_at_ms']
             and record['age_anchor_at_ms'] <= record['publication_at_ms'], 'news-time-order')
    need(isinstance(record['relevances'], list) and len(record['relevances']) <= 100, 'relevance-budget')
    for rel in record['relevances']:
        need(isinstance(rel, dict) and set(rel) == RELEVANCE_KEYS, 'relevance-schema')
        need(isinstance(rel['code'], str) and re.fullmatch(r'US\.[A-Z][A-Z0-9.-]{0,63}', rel['code']), 'invalid-relevance-code')
        security = rel['security_id']
        need(type(security) is int and 0 < security < 2**63 or isinstance(security, str)
             and re.fullmatch('[0-9]{1,19}', security) is not None and 0 < int(security) < 2**63, 'invalid-relevance-id')
        need(all(text(rel[k]) for k in ('target_entity_id', 'target_aspect', 'sentiment_scope', 'subject_identity')), 'invalid-relevance-subject')
        need(_member(rel['relevance_kind'], KINDS) and _member(rel['status'], {'verified', 'unavailable'})
             and (rel['reason'] is None or text(rel['reason'])), 'invalid-relevance-status')
        need(hashed(rel['evidence_hash']) and (rel['known_at_ms'] is None or stamp(rel['known_at_ms'])), 'invalid-relevance-evidence')


def _record_budget(records, limits=LIMITS):
    need(isinstance(records, list) and len(records) <= limits['articles'], 'article-budget')
    total = 0
    anchors, envelopes = {}, {}
    for record in records:
        _validate_record(record)
        anchor = (record['first_seen_at_ms'], record['age_anchor_at_ms'])
        article = record['article_id']
        need(article not in anchors or anchors[article] == anchor, 'revision-freshness-anchor-changed')
        anchors[article] = anchor
        version = (article, record['revision_known_at_ms'])
        need(version not in envelopes or envelopes[version] == record, 'conflicting-same-time-revision')
        envelopes[version] = record
        size = len((record['headline'] + record['permitted_text']).encode())
        need(size <= limits['article_text_bytes'], 'article-text-budget')
        total += size
    need(total <= limits['total_text_bytes'], 'aggregate-text-budget')
    need(len(encoded(records)) <= limits['cache_bytes'], 'cache-artifact-budget')


def normalize_supplied_news(entries, source_receipt, policy):
    need(isinstance(entries, list) and len(entries) <= MAX_ARTICLES, 'article-budget')
    need(isinstance(source_receipt, dict) and set(source_receipt) == {'source_id', 'source_url', 'source_receipt_hash'}, 'source-receipt-schema')
    need(text(source_receipt['source_id']) and url(source_receipt['source_url'])
         and hashed(source_receipt['source_receipt_hash']), 'source-receipt-schema')
    need(isinstance(policy, dict) and source_receipt['source_id'] == policy.get('source_id')
         and source_receipt['source_url'] == policy.get('source_url'), 'source-receipt-mismatch')
    result = []
    for original in entries:
        need(isinstance(original, dict), 'news-record-schema')
        need('schema_version' not in original or type(original['schema_version']) is int, 'news-record-schema')
        record = deepcopy(original)
        for key, value in source_receipt.items():
            need(key not in record or record[key] == value, 'source-receipt-mismatch')
            record[key] = value
        for key, value in {'schema_version': 1, 'policy_hash': digest(policy)}.items():
            need(key not in record or record[key] == value, 'policy-binding-mismatch')
            record[key] = value
        article = digest([record.get('source_id'), record.get('canonical_url')])
        content = digest([record.get(k) for k in ('headline', 'permitted_text', 'text_scope', 'language')])
        derived = {'article_id': article, 'content_hash': content,
                   'text_version_id': digest([article, content, record.get('publication_at_ms'), record.get('revision_known_at_ms')])}
        for key, value in derived.items():
            need(key not in record or record[key] == value, 'supplied-id-hash-mismatch')
            record[key] = value
        result.append(record)
    _record_budget(result, _limits(policy))
    return result


def select_news_as_of(records, cutoff_ms, policy):
    need(stamp(cutoff_ms), 'invalid-news-input')
    _record_budget(records)
    policies = policy if isinstance(policy, list) else [policy]
    need(0 < len(policies) <= MAX_SOURCES, 'source-budget')
    permissions = [validate_source_policy(p, cutoff_ms) for p in policies]
    need(all(text(p.get('source_id'), 64) for p in policies), 'invalid-source-id')
    need(len({p['source_id'] for p in policies}) == len(policies), 'invalid-source-id')
    sources = {p['source_id']: (p, permission) for p, permission in zip(policies, permissions)}
    for source_id, (p, permission) in sources.items():
        if permission['status'] == 'permitted':
            _record_budget([r for r in records if r['source_id'] == source_id], _limits(p))
    latest, rejected, anchors = {}, [], {}
    def reject(value):
        need(len(rejected) < MAX_SELECTED, 'rejection-row-budget')
        rejected.append(value)
    for record in records:
        key = record['article_id']
        anchor = (record['first_seen_at_ms'], record['age_anchor_at_ms'])
        need(key not in anchors or anchors[key] == anchor, 'revision-freshness-anchor-changed')
        anchors[key] = anchor
        source = sources.get(record['source_id'])
        policy, permission = source if source else ({}, {'status': 'disabled'})
        required = [record[k] for k in MS_FIELDS] + [policy.get('known_at_ms')]
        reason = None
        if permission['status'] != 'permitted':
            reason = 'source-policy-disabled'
        elif (record['policy_hash'] != permission['policy_hash'] or record['source_id'] != policy['source_id']
              or record['source_url'] != policy['source_url'] or record['text_scope'] not in policy['text_scopes']
              or (record['rights_known_at_ms'] is not None and record['rights_known_at_ms'] < policy['known_at_ms'])):
            reason = 'policy-binding-mismatch'
        elif any(t is None for t in required):
            reason = 'required-time-unavailable'
        elif max(required) > cutoff_ms:
            reason = 'future-evidence'
        elif cutoff_ms - record['age_anchor_at_ms'] > policy['max_age_ms']:
            reason = 'stale-event'
        if reason:
            reject({'article_id': key, 'text_version_id': record['text_version_id'], 'reason': reason})
            continue
        old = latest.get(key)
        if old is not None and record['revision_known_at_ms'] == old['revision_known_at_ms']:
            need(record == old, 'conflicting-same-time-revision')
        if old is None or record['revision_known_at_ms'] > old['revision_known_at_ms']:
            latest[key] = record
    events = {}
    output_text_bytes = 0
    output_json_bytes = 2
    for record in latest.values():
        usable = False
        for rel in record['relevances']:
            if rel['status'] != 'verified' or rel['known_at_ms'] is None or rel['known_at_ms'] > cutoff_ms:
                reject({'article_id': record['article_id'], 'text_version_id': record['text_version_id'],
                                 'relevance': deepcopy(rel), 'reason': 'relevance-unverified' if rel['status'] != 'verified'
                                 else 'relevance-time-unavailable' if rel['known_at_ms'] is None else 'future-relevance'})
                continue
            usable = True
            key = (record['event_id'], rel['code'], type(rel['security_id']).__name__, rel['security_id'],
                   rel['target_entity_id'], rel['target_aspect'], rel['sentiment_scope'], rel['relevance_kind'], rel['subject_identity'])
            old = events.get(key)
            if old is not None:
                need(old['age_anchor_at_ms'] == record['age_anchor_at_ms'], 'event-freshness-anchor-conflict')
                if old['article_id'] == record['article_id']:
                    need(old['relevances'] == [rel], 'conflicting-relevance')
            if old is None or (record['first_seen_at_ms'], record['article_id']) < (old['first_seen_at_ms'], old['article_id']):
                need(old is not None or len(events) < MAX_SELECTED, 'selected-row-budget')
                # Check expansion bounds before deep-copying the potentially repeated text.
                candidate = record | {'relevances': [rel]}
                output_text_bytes += len((record['headline'] + record['permitted_text']).encode()) - (len((old['headline'] + old['permitted_text']).encode()) if old else 0)
                output_json_bytes += len(encoded(candidate)) + 1 - (len(encoded(old)) + 1 if old else 0)
                need(output_text_bytes <= MAX_TOTAL_TEXT, 'selected-text-budget')
                need(output_json_bytes <= MAX_CACHE, 'selected-cache-budget')
                candidate = deepcopy(candidate)
                events[key] = candidate
        if not usable:
            reject({'article_id': record['article_id'], 'text_version_id': record['text_version_id'], 'reason': 'verified-relevance-unavailable'})
    result = {'schema_version': 1, 'cutoff_ms': cutoff_ms, 'status': 'available' if events else 'unavailable',
            'policies': [deepcopy(p) if r['status'] == 'permitted' else {'source_id': p['source_id'], 'enabled': False} for p, r in zip(policies, permissions)],
            'source_dispositions': [dict(source_id=p['source_id'], **r) for p, r in zip(policies, permissions)],
            'records': sorted(events.values(), key=lambda r: (r['event_id'], r['article_id'], encoded(r['relevances']))),
            'rejected': rejected, 'coverage': {'input_articles': len(records),
            'eligible_article_revisions': len(latest), 'unique_event_subjects': len(events),
            'unique_events': len({r['event_id'] for r in events.values()}),
            'rejected_relevances': sum('relevance' in r for r in rejected),
            'complete_source_coverage': False}, 'forecast_use_allowed': False}
    need(len(encoded(result)) <= MAX_CACHE, 'selected-cache-budget')
    return result


def empty_cache():
    return {'schema_version': 1, 'records': [], 'sources': {}, 'attempts': []}


def _validate_state(state):
    need(isinstance(state, dict) and set(state) == STATE_KEYS, 'invalid-collection-cache')
    need(hashed(state['policy_hash']) and url(state['endpoint']), 'invalid-collection-cache')
    for key in ('etag', 'last_modified'):
        need(state[key] is None or text(state[key], 256) and not SECRET.search(state[key]), 'invalid-collection-cache')
    need(state['etag'] is None or re.fullmatch(r'(?:W/)?"[A-Za-z0-9._:-]{1,128}"', state['etag']), 'invalid-collection-cache')
    if state['last_modified'] is not None:
        _publication(state['last_modified'])
    need(state['body_hash'] is None or hashed(state['body_hash']), 'invalid-collection-cache')
    for key in ('checked_at_ms', 'next_allowed_at_ms', 'attempted_at_ms'):
        need(state[key] is None or stamp(state[key]), 'invalid-collection-cache')
    need(state['checked_at_ms'] is None or state['attempted_at_ms'] is not None
         and state['checked_at_ms'] >= state['attempted_at_ms'], 'invalid-collection-cache')


def _validate_cache(cache):
    need(isinstance(cache, dict) and set(cache) == {'schema_version', 'records', 'sources', 'attempts'}
         and type(cache['schema_version']) is int and cache['schema_version'] == 1, 'invalid-collection-cache')
    _record_budget(cache['records'])
    need(isinstance(cache['sources'], dict) and len(cache['sources']) <= MAX_SOURCES, 'source-budget')
    for key, state in cache['sources'].items():
        need(text(key, 64) and not SECRET.search(key) and re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', key), 'invalid-collection-cache')
        _validate_state(state)
    need(isinstance(cache['attempts'], list) and len(cache['attempts']) <= MAX_ARTICLES, 'invalid-collection-cache')
    for attempt in cache['attempts']:
        need(isinstance(attempt, dict) and set(attempt) == {'source_id', 'at_ms'}
             and text(attempt['source_id'], 64) and stamp(attempt['at_ms']), 'invalid-collection-cache')
    need(len(encoded(cache)) <= MAX_CACHE, 'cache-artifact-budget')


def _receipt(source_id, status, reason, state=None):
    base = {k: None for k in STATE_KEYS}
    if state:
        base.update(state)
    return base | {'source_id': source_id, 'status': status, 'reason': reason}


def _publication(raw):
    need(text(raw, 128), 'invalid-original-time')
    try:
        try:
            value = parsedate_to_datetime(raw)
        except ValueError:
            value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        need(value.tzinfo is not None and value.utcoffset() is not None, 'invalid-original-time')
        timestamp = int(value.timestamp() * 1000)
        need(stamp(timestamp), 'invalid-original-time')
        return timestamp, value.strftime('%z')
    except (ValueError, TypeError, OverflowError):
        raise NewsError('invalid-original-time') from None


def _feed(body, policy, now, previous):
    # Decode first: scanning raw ASCII misses UTF16 declarations/DTD/entities.
    try:
        xml = body.decode('utf-8-sig')
    except UnicodeError:
        raise NewsError('unsafe-xml') from None
    need(not re.search(r'<!\s*(DOCTYPE|ENTITY)', xml, re.I), 'unsafe-xml')
    try:
        root = ET.fromstring(xml)
    except (ET.ParseError, ValueError):
        raise NewsError('invalid-feed') from None
    atom = '{http://www.w3.org/2005/Atom}'
    if root.tag == 'rss' and root.get('version') == '2.0':
        channels = root.findall('channel')
        need(len(channels) == 1 and len(root) == 1, 'invalid-feed')
        items = channels[0].findall('item')
        need(not any(e.tag == 'item' for e in root.iter() if e not in items), 'invalid-feed')
        kind = 'rss'
    else:
        need(root.tag == atom + 'feed', 'invalid-feed')
        items = root.findall(atom + 'entry')
        need(not any(e.tag == atom + 'entry' for e in root.iter() if e not in items), 'invalid-feed')
        kind = 'atom'
    need(len(items) <= _limits(policy)['articles'], 'article-budget')
    records = []
    receipt_hash = digest({'source_id': policy['source_id'], 'policy_hash': digest(policy), 'body_hash': hashlib.sha256(body).hexdigest(), 'at_ms': now})
    for item in items:
        def one(name, required=True):
            values = item.findall(name)
            need(len(values) == 1 if required else len(values) <= 1, 'invalid-feed')
            if not values:
                return None
            need(len(values[0]) == 0, 'invalid-feed')
            return values[0].text or ''
        if kind == 'rss':
            headline, link, publication = one('title'), one('link'), one('pubDate')
            description = one('description', False) or ''
        else:
            headline, publication = one(atom + 'title'), one(atom + 'published')
            links = [e for e in item.findall(atom + 'link') if e.get('rel', 'alternate') == 'alternate']
            need(len(links) == 1 and len(links[0]) == 0, 'invalid-feed')
            link = links[0].get('href')
            description = one(atom + 'summary', False) or ''
        need(url(link), 'invalid-feed')
        published, zone = _publication(publication)
        # Escaped HTML is not silently stripped/truncated into different evidence.
        need(not any(c in headline + description for c in '<>'), 'invalid-feed')
        scope = 'full-permitted' if 'full-permitted' in policy['text_scopes'] else 'headline-only'
        article_id = digest([policy['source_id'], link])
        old = [r for r in previous if r['article_id'] == article_id]
        old = max(old, key=lambda r: r['revision_known_at_ms'] or 0) if old else None
        record = {'canonical_url': link, 'headline': headline, 'permitted_text': description if scope == 'full-permitted' else '',
                  'text_scope': scope, 'language': 'und', 'publication_raw': publication,
                  'publication_timezone': zone, 'relevances': [], 'event_id': article_id,
                  'dedup_version': 'article-identity-only-v1', 'dedup_evidence_hash': receipt_hash,
                  'representative_evidence_hash': receipt_hash, 'publication_at_ms': published,
                  'first_seen_at_ms': old['first_seen_at_ms'] if old else now,
                  'age_anchor_at_ms': old['age_anchor_at_ms'] if old else published,
                  'retrieved_at_ms': now, 'revision_known_at_ms': now, 'ingestion_at_ms': now,
                  'rights_known_at_ms': policy['known_at_ms'], 'dedup_known_at_ms': now, 'representative_known_at_ms': now}
        normalized = normalize_supplied_news([record], {'source_id': policy['source_id'], 'source_url': policy['source_url'],
                                                       'source_receipt_hash': receipt_hash}, policy)[0]
        if old and old['content_hash'] == normalized['content_hash'] and old['publication_at_ms'] == published:
            normalized = deepcopy(old)  # Never refresh known time/rights or original age for same text.
        records.append(normalized)
    need(len({r['article_id'] for r in records}) == len(records), 'invalid-feed')
    _record_budget(records, _limits(policy))
    return records


def _response(response, endpoint, cap):
    need(isinstance(response, NewsResponse) and type(response.status) is int
         and isinstance(response.body, bytes) and isinstance(response.headers, dict)
         and response.url in (None, endpoint), 'invalid-response')
    need(len(response.body) <= cap, 'response-budget')
    need(len(response.headers) <= 32, 'invalid-response')
    result = {}
    for key, value in response.headers.items():
        need(text(key, 64) and text(value, 256, empty=True), 'invalid-response')
        lower = key.lower()
        if lower in {'etag', 'last-modified', 'retry-after'}:
            need(lower not in result and not SECRET.search(value), 'invalid-response')
            result[lower] = value
    return result


def _retry_after(value, now, interval):
    if value is None:
        return now + interval
    try:
        if re.fullmatch('[0-9]{1,8}', value):
            return max(now + interval, now + int(value) * 1000)
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is not None:
            return max(now + interval, int(parsed.timestamp() * 1000))
    except (ValueError, TypeError, OverflowError):
        pass
    return now + interval


def collect_configured_news(policies, *, transport=None, clock_ms, cache=None, mode='off'):
    need(_member(mode, {'off', 'offline', 'collect'}), 'invalid-collection-mode')
    need(isinstance(policies, (list, tuple)) and len(policies) <= MAX_SOURCES, 'source-budget')
    def clock():
        try:
            return clock_ms()
        except Exception:
            raise NewsError('invalid-clock') from None
    now = clock()
    run_started = now
    need(stamp(now), 'invalid-clock')
    cache = empty_cache() if cache is None else cache
    _validate_cache(cache)
    permissions = [validate_source_policy(p, now) for p in policies]
    identities = [p.get('source_id') for p in policies]
    need(all(text(s, 64) and not SECRET.search(s) and re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', s) for s in identities)
         and len(set(identities)) == len(identities), 'invalid-source-id')
    need(len(set(identities) | set(cache['sources'])) <= MAX_SOURCES, 'source-budget')
    receipts = []
    calls = 0
    for policy, permission in zip(policies, permissions):
        source = policy['source_id']
        old_state = cache['sources'].get(source)
        if mode != 'collect' or permission['status'] != 'permitted':
            receipts.append(_receipt(source, 'disabled', mode if mode != 'collect' else permission['reason'], old_state))
            continue
        now = clock()
        need(stamp(now) and now >= run_started, 'invalid-clock')
        interval = policy['poll_interval_ms']
        # Keep previous backoff across changed policy; a new permission cannot erase attempts.
        attempts = [a['at_ms'] for a in cache['attempts'] if a['source_id'] == source]
        due = max(attempts, default=0) + interval if attempts else 0
        if old_state and old_state['next_allowed_at_ms'] is not None:
            due = max(due, old_state['next_allowed_at_ms'])
        if due > now:
            receipts.append(_receipt(source, 'unavailable', 'backoff' if old_state and due > (old_state['attempted_at_ms'] or 0) + interval else 'poll-not-due', old_state))
            continue
        recent = sum(a['at_ms'] > now - 60000 for a in cache['attempts'])
        if calls >= MAX_SOURCES or recent >= MAX_SOURCES:
            receipts.append(_receipt(source, 'unavailable', 'request-budget', old_state))
            continue
        if not callable(transport):
            receipts.append(_receipt(source, 'unavailable', 'transport-unavailable', old_state))
            continue
        state = {'policy_hash': permission['policy_hash'], 'endpoint': policy['endpoint'], 'etag': None,
                 'last_modified': None, 'body_hash': None, 'checked_at_ms': None,
                 'attempted_at_ms': now, 'next_allowed_at_ms': now + interval}
        if old_state and old_state['policy_hash'] == permission['policy_hash'] and old_state['endpoint'] == policy['endpoint']:
            state.update({k: old_state[k] for k in ('etag', 'last_modified', 'body_hash')})
        headers = [('Accept', 'application/rss+xml, application/atom+xml, application/xml')]
        for key, name in (('etag', 'If-None-Match'), ('last_modified', 'If-Modified-Since')):
            if state[key] is not None:
                headers.append((name, state[key]))
        calls += 1
        cache['attempts'] = [a for a in cache['attempts'] if a['at_ms'] > now - 60000]
        cache['attempts'].append({'source_id': source, 'at_ms': now})
        cache['sources'][source] = state  # Attempt/backoff survives every failure; no same-run retry.
        try:
            response = transport(NewsRequest(policy['endpoint'], tuple(headers), max_bytes=_limits(policy)['response_bytes']))
        except Exception:
            receipts.append(_receipt(source, 'unavailable', 'transport-failure', state))
            continue
        try:
            observed = clock()
            need(stamp(observed) and observed >= now, 'invalid-response-clock')
            need(observed - now <= 10000, 'transport-timeout')
            response_headers = _response(response, policy['endpoint'], _limits(policy)['response_bytes'])
            validators = state | {k: response_headers.get(h) for k, h in (('etag', 'etag'), ('last_modified', 'last-modified'))}
            _validate_state(validators)
            if response.status in (429, 503):
                state['next_allowed_at_ms'] = _retry_after(response_headers.get('retry-after'), observed, interval)
                reason = 'retry-after'
            elif response.status == 304:
                need(state['body_hash'] is not None and not response.body, 'invalid-response')
                state['checked_at_ms'] = observed
                reason = 'not-modified'
            elif response.status == 200:
                body_hash = hashlib.sha256(response.body).hexdigest()
                if body_hash == state['body_hash']:
                    reason = 'unchanged'
                else:
                    incoming = _feed(response.body, policy, observed, cache['records'])
                    revisions = {r['text_version_id']: deepcopy(r) for r in cache['records']}
                    for record in incoming:
                        revisions[record['text_version_id']] = record
                    combined = list(revisions.values())
                    _record_budget(combined, _limits(policy))
                    need(len(encoded(cache | {'records': combined})) <= _limits(policy)['cache_bytes'], 'cache-artifact-budget')
                    cache['records'] = combined
                    reason = 'collected'
                state.update({'body_hash': body_hash, 'checked_at_ms': observed,
                              'etag': response_headers.get('etag'), 'last_modified': response_headers.get('last-modified')})
            else:
                reason = 'http-error'
            receipts.append(_receipt(source, 'available' if reason in {'not-modified', 'unchanged', 'collected'} else 'unavailable', reason, state))
        except NewsError as exc:
            reason = str(exc) if str(exc) in REASONS else 'invalid-feed'
            receipts.append(_receipt(source, 'rejected', reason, state))
    _validate_cache(cache)
    return {'schema_version': 1, 'records': deepcopy(cache['records']), 'receipts': receipts,
            'cache': deepcopy(cache), 'complete_source_coverage': False, 'forecast_use_allowed': False}


def _private_parent(output_parent, *, create=True):
    raw = Path(output_parent).expanduser().absolute()
    need(not any(p.is_symlink() for p in (raw, *raw.parents)), 'unsafe-cache-path')
    parent = raw.resolve()
    need(not parent.is_relative_to(REPO_ROOT) and not any((p / '.git').exists() for p in (parent, *parent.parents)), 'news-cache-must-be-outside-repository')
    if not parent.exists() and not create:
        return parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = parent.stat()
    need(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'cache-parent-permissions')
    return parent


def _validate_receipts(receipts):
    need(isinstance(receipts, list) and len(receipts) <= MAX_SOURCES, 'cache-receipt-fields')
    for receipt in receipts:
        need(isinstance(receipt, dict) and set(receipt) == RECEIPT_KEYS, 'cache-receipt-fields')
        need(text(receipt['source_id'], 64) and not SECRET.search(receipt['source_id']) and re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', receipt['source_id']) and _member(receipt['status'], {'disabled', 'available', 'unavailable', 'rejected'})
             and _member(receipt['reason'], REASONS), 'cache-receipt-fields')
        state = {k: receipt[k] for k in STATE_KEYS}
        if state['policy_hash'] is None:
            need(all(v is None for v in state.values()) and receipt['status'] in {'disabled', 'unavailable'}, 'cache-receipt-fields')
        else:
            _validate_state(state)
    need(len({r['source_id'] for r in receipts}) == len(receipts), 'cache-receipt-fields')


def append_cache_generation(records, receipts, *, output_parent, generated_at=None):
    _record_budget(records)
    _validate_receipts(receipts)
    news_data = {'schema_version': 1, 'records': records}
    need(len(encoded(news_data)) + len(encoded(receipts)) + 65536 <= MAX_CACHE, 'cache-artifact-budget')
    parent = _private_parent(output_parent)
    generation = Generation(parent, generated_at=generated_at, kind='stock-research-news-cache')
    generation.json('news.json', news_data)
    generation.json('receipts.json', receipts)
    return generation.finish(news_schema_version=1, status='supplied-cached-only', source_activation=False)


def _bounded_private_read(path, cap):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
             and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size <= cap, 'cache-read-budget')
        data = stream.read(cap + 1)
        need(len(data) <= cap, 'cache-read-budget')
        return data


def read_collection_cache(parent):
    # Reject whole-parent overflow. Repeated unchanged generations deduplicate by
    # exact text_version_id; no unbounded parse, silent history window or pruning.
    parent = _private_parent(parent, create=False)
    cache = empty_cache()
    revisions = {}
    if not parent.exists():
        return cache
    try:
        folders = []
        for folder in parent.iterdir():
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{6}', folder.name):
                continue
            need(not folder.is_symlink() and folder.is_dir(), 'unsafe-cache-path')
            if not (folder / 'manifest.json').exists():
                continue  # Unfinished generation never supplies cached evidence.
            folders.append(folder)
            need(len(folders) <= MAX_GENERATIONS, 'cache-generation-budget')
        total_bytes = 0
        for folder in sorted(folders):
            info = folder.stat()
            need(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'cache-parent-permissions')
            manifest_data = _bounded_private_read(folder / 'manifest.json', 65536)
            manifest = json.loads(manifest_data)
            need(isinstance(manifest, dict) and manifest.get('schema_version') == 1
                 and type(manifest.get('schema_version')) is int
                 and manifest.get('kind') == 'stock-research-news-cache'
                 and manifest.get('news_schema_version') == 1 and type(manifest.get('news_schema_version')) is int, 'cache-schema')
            timestamp = datetime.fromisoformat(manifest['generated_at'])
            from zoneinfo import ZoneInfo
            need(timestamp.tzinfo is not None and timestamp.astimezone(ZoneInfo('Asia/Kuala_Lumpur')).strftime('%Y-%m-%d_%H%M%S') == folder.name, 'cache-schema')
            entries = manifest.get('artifacts')
            need(isinstance(entries, dict) and set(entries) == {'news.json', 'receipts.json'}, 'cache-schema')
            for name, entry in entries.items():
                need(isinstance(entry, dict) and set(entry) == {'path', 'sha256', 'bytes'}
                     and entry['path'] == name and hashed(entry['sha256']) and type(entry['bytes']) is int
                     and 0 <= entry['bytes'] <= MAX_CACHE, 'cache-read-budget')
            total_bytes += len(manifest_data) + sum(e['bytes'] for e in entries.values())
            need(total_bytes <= MAX_CACHE, 'cache-read-budget')
            payloads = {}
            for name, entry in entries.items():
                data = _bounded_private_read(folder / name, entry['bytes'])
                need(len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'], 'cache-hash-mismatch')
                payloads[name] = json.loads(data)
            value = payloads['news.json']
            need(isinstance(value, dict) and set(value) == {'schema_version', 'records'}
                 and type(value['schema_version']) is int and value['schema_version'] == 1, 'cache-schema')
            _record_budget(value['records'])
            receipts = payloads['receipts.json']
            _validate_receipts(receipts)
            for record in value['records']:
                old = revisions.get(record['text_version_id'])
                need(old is None or old == record, 'conflicting-cached-revision')
                revisions[record['text_version_id']] = record
            cache['records'] = list(revisions.values())
            _record_budget(cache['records'])
            for receipt in receipts:
                state = {k: receipt[k] for k in STATE_KEYS}
                if state['policy_hash'] is not None:
                    cache['sources'][receipt['source_id']] = state
                    if state['attempted_at_ms'] is not None:
                        attempt = {'source_id': receipt['source_id'], 'at_ms': state['attempted_at_ms']}
                        if attempt not in cache['attempts']:
                            cache['attempts'].append(attempt)
        _validate_cache(cache)
        return cache
    except (StorageError, OSError, ValueError, TypeError, KeyError, RecursionError):
        raise NewsError('invalid-news-cache') from None


def read_cache_generations(parent):
    return read_collection_cache(parent)['records']
