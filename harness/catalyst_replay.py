"""Pure synthetic temporal replay; no evidence lookup, scoring or causal inference."""
from copy import deepcopy
from datetime import datetime
from itertools import combinations
import unicodedata
from urllib.parse import urlsplit

SPLITS = ('train', 'calibration', 'test')
TIMES = ('published_at', 'provider_available_at', 'first_observed_at', 'ingested_at')
LABELS = ('plausible_catalyst', 'context_correlation', 'contradictory', 'unknown')


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + ' requires nonempty text')
    return value


def _time(value, field):
    if not isinstance(value, str) or 'T' not in value:
        raise ValueError(field + ' requires aware ISO timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.utcoffset() is None:
            raise ValueError('timezone missing')
        return parsed
    except (ValueError, OverflowError):
        raise ValueError(field + ' requires aware ISO timestamp') from None


def _url(value):
    _text(value, 'source_url')
    if any(ord(char) <= 32 or unicodedata.category(char) in ('Cc', 'Cf') for char in value) or '\\' in value:
        raise ValueError('unsafe source_url')
    try:
        url = urlsplit(value)
        url.port  # Validate deferred port parsing, including range.
        if url.scheme.lower() not in ('http', 'https') or not url.hostname or url.username is not None or url.password is not None:
            raise ValueError('unsafe source_url')
    except ValueError:
        raise ValueError('unsafe source_url') from None


def _news(item, cutoff, review):
    if not isinstance(item, dict):
        raise ValueError('news requires an object')
    for field in ('news_id', 'source', 'provider', 'provenance_ref', 'event_cluster_id', 'revision_id'):
        _text(item.get(field), field)
    _url(item.get('source_url'))
    if item.get('annotation_label') not in LABELS:
        raise ValueError('invalid annotation_label')
    precision = item.get('timestamp_precision')
    if precision not in ('timestamp', 'date', 'unknown'):
        raise ValueError('invalid timestamp_precision')
    reasons, instants = [], {}
    if precision != 'timestamp':
        reasons.append('timestamp_precision_' + precision)
    for field in TIMES:
        if field not in item:
            raise ValueError(field + ' requires aware timestamp or explicit null')
        instant = _time(item[field], field) if item[field] is not None else None
        instants[field] = instant
        if instant is None:
            reasons.append(field + '_unknown')
        else:
            if instant > cutoff:
                reasons.append(field + '_after_information_cutoff')
            if instant > review:
                reasons.append(field + '_after_review_at')
    ordered = True
    for earlier, later in combinations(TIMES, 2):
        if instants[earlier] is not None and instants[later] is not None and instants[earlier] > instants[later]:
            reasons.append('timestamp_order_' + earlier + '_' + later)
            ordered = False
    known = precision == 'timestamp' and all(value is not None for value in instants.values()) and ordered
    prospective = known and all(value <= cutoff for value in instants.values())
    explanation = known and all(value <= review for value in instants.values()) and not prospective
    return {'evidence': deepcopy(item), 'prospective_eligible': prospective,
            'availability': 'prospective' if prospective else 'explanation_only' if explanation else 'unavailable',
            'reason_codes': reasons}


def replay_cases(envelope):
    """Return every authored case/revision and separate temporal/fold diagnostics."""
    if not isinstance(envelope, dict) or type(envelope.get('schema_version')) is not int or envelope['schema_version'] != 1:
        raise ValueError('schema_version must be 1')
    if envelope.get('origin') != 'synthetic':
        raise ValueError('only synthetic envelopes supported')
    decision = _time(envelope.get('decision_cutoff'), 'decision_cutoff')
    review = _time(envelope.get('review_at'), 'review_at')
    if review < decision:
        raise ValueError('review_at precedes decision_cutoff')
    if not isinstance(envelope.get('cases'), list):
        raise ValueError('cases requires an explicit list')
    cases, timings, identities, parents = [], [], set(), {}

    def root(cluster):
        parents.setdefault(cluster, cluster)
        current = cluster
        while parents[current] != current:
            current = parents[current]
        while parents[cluster] != cluster:
            parent = parents[cluster]
            parents[cluster] = current
            cluster = parent
        return current

    def link(left, right):
        a, b = root(left), root(right)
        parents[max(a, b)] = min(a, b)

    for case in envelope['cases']:
        if not isinstance(case, dict):
            raise ValueError('case requires an object')
        for field in ('case_id', 'instrument', 'venue', 'currency', 'event_cluster_id'):
            _text(case.get(field), field)
        if case['case_id'] in identities:
            raise ValueError('duplicate case_id')
        identities.add(case['case_id'])
        if case.get('split') not in SPLITS:
            raise ValueError('invalid split')
        cutoff = _time(case.get('information_cutoff'), 'information_cutoff')
        start = _time(case.get('outcome_start'), 'outcome_start')
        end = _time(case.get('outcome_end'), 'outcome_end')
        if cutoff > decision or cutoff >= start or start > end:
            raise ValueError('invalid information cutoff or outcome interval')
        if not isinstance(case.get('news'), list):
            raise ValueError('news requires an explicit list')
        cluster = case['event_cluster_id']
        root(cluster)
        news, seen = [], set()
        for item in case['news']:
            result = _news(item, cutoff, review)
            if item['news_id'] in seen:
                raise ValueError('duplicate per-case news_id')
            seen.add(item['news_id'])
            link(cluster, item['event_cluster_id'])  # Includes unknown/future evidence links.
            news.append(result)
        cases.append({'case': deepcopy(case), 'prospective_eligible': True, 'reason_codes': [],
                      'outcome_status': 'available' if end <= review else 'pending', 'news': news})
        timings.append((case, cutoff, start, end))

    components = {}
    for case, _, _, _ in timings:
        components.setdefault(root(case['event_cluster_id']), []).append(case)
    violations = []
    for component, members in sorted(components.items()):
        splits = sorted({case['split'] for case in members}, key=SPLITS.index)
        if len(splits) > 1:
            violations.append({'code': 'cluster_crosses_splits', 'component_id': component,
                               'case_ids': [case['case_id'] for case in members], 'splits': splits})
    for earlier_rank, earlier_split in enumerate(SPLITS):
        for later_split in SPLITS[earlier_rank + 1:]:
            earlier = [row for row in timings if row[0]['split'] == earlier_split]
            later = [row for row in timings if row[0]['split'] == later_split]
            if not earlier or not later:
                continue
            fitting = min(row[1] for row in later)
            later_ids = [row[0]['case_id'] for row in later if row[1] == fitting]
            for case, cutoff, start, end in earlier:
                details = {'case_id': case['case_id'], 'earlier_split': earlier_split,
                           'later_split': later_split, 'later_case_ids': later_ids}
                if cutoff >= fitting:
                    violations.append({'code': 'split_cutoff_order', **details})
                if end > fitting:
                    violations.append({'code': 'outcome_unavailable_at_fitting_cutoff', **details})
                    if start <= fitting:
                        violations.append({'code': 'outcome_overlaps_fitting_cutoff', **details})
    all_news = [item for case in cases for item in case['news']]
    eligible = sum(item['prospective_eligible'] for item in all_news)
    return {'schema_version': 1, 'origin': 'synthetic', 'decision_cutoff': envelope['decision_cutoff'],
            'review_at': envelope['review_at'], 'cases': cases, 'folds_valid': not violations,
            'violations': violations, 'summary': {
                'case_count': len(cases), 'prospective_eligible_case_count': len(cases),
                'prospective_excluded_case_count': 0, 'empty_news_case_count': sum(not case['news'] for case in cases),
                'news_count': len(all_news), 'prospective_eligible_news_count': eligible,
                'prospective_excluded_news_count': len(all_news) - eligible,
                'explanation_only_news_count': sum(item['availability'] == 'explanation_only' for item in all_news),
                'unavailable_news_count': sum(item['availability'] == 'unavailable' for item in all_news),
                'unique_cluster_id_count': len(parents), 'connected_component_count': len(components),
                'pending_outcome_case_count': sum(case['outcome_status'] == 'pending' for case in cases)}}
