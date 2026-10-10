"""Synthetic-only, in-memory outcome metadata assessment; never scores or writes.

The caller supplies all fixtures. A matching digest establishes byte identity only.
Source classes and rights declarations are simulated, not independently verified.
"""
from datetime import date, datetime, timezone
import hashlib
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SOURCE_CLASSES = {'vendor_reported_bar', 'exchange_certified_close'}
ADJUSTMENTS = {'unadjusted', 'split_adjusted', 'total_return_adjusted'}
BINDING_FIELDS = ('forecast_id', 'ledger_revision', 'market', 'listing_id', 'ticker',
                  'forecast_cutoff', 'reference_session', 'target_session',
                  'horizon_kind', 'horizon_count', 'instruments_version',
                  'calendar_version', 'mic_version')
SEMANTICS = ('source_class', 'observation_kind', 'price_field', 'adjustment_basis',
             'corporate_action_treatment', 'series_vintage')


def _mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(label + ':object_required')
    return value


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ':nonempty_string_required')
    return value


def _day(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError(label + ':invalid_date')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(label + ':invalid_date') from None


def _instant(value, label, utc=False):
    if not isinstance(value, str):
        raise ValueError(label + ':aware_timestamp_required')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError(label + ':invalid_timestamp') from None
    if result.utcoffset() is None or (utc and result.utcoffset().total_seconds() != 0):
        raise ValueError(label + ':utc_timestamp_required' if utc else label + ':aware_timestamp_required')
    return result.astimezone(timezone.utc)


def assess_outcome(record, *, fixtures, review_at):
    """Return deterministic gate statuses for a v2 synthetic metadata record.

    ``fixtures`` contains versioned synthetic ``ledger``, ``instruments`` and
    ``calendar`` objects and an ``evidence`` mapping from IDs to immutable JSON
    bytes. Listing intervals use inclusive effective_from/exclusive effective_to.
    Malformed inputs return blocked reasons. No provider, file or scoring access.
    """
    reasons = set()
    result = dict(maturity='unknown', provenance_status='blocked',
                  rights_status='unverified', review_status='pending',
                  assessment_status='blocked')

    def require(condition, reason):
        if not condition:
            reasons.add(reason)

    try:
        record = _mapping(record, 'record')
        if type(record.get('schema_version')) is int and record['schema_version'] == 1:
            result['provenance_status'] = 'legacy_unverifiable'
            reasons.add('legacy_v1_not_assessed')
            return dict(result, reasons=sorted(reasons))
        require(type(record.get('schema_version')) is int and record['schema_version'] == 2,
                'schema_version_2_required')
        require(record.get('synthetic') is True, 'synthetic_record_required')
        require(record.get('market') == 'US', 'us_only')
        result['rights_status'] = 'denied' if record.get('rights_declaration') == 'denied' else 'unverified'
        require(record.get('rights_declaration') == 'synthetic_only', 'rights_not_synthetic_only')
        review = record.get('review_state')
        result['review_status'] = review if review in {'requested', 'pending', 'denied'} else 'pending'
        require(review == 'requested', 'human_review_not_requested')
        now = _instant(review_at, 'review_at')
        cutoff = _instant(record.get('forecast_cutoff'), 'forecast_cutoff')
        require(cutoff <= now, 'forecast_after_review')
        reference_day = _day(record.get('reference_session'), 'reference_session')
        target_day = _day(record.get('target_session'), 'target_session')
        require(reference_day < target_day, 'target_not_after_reference')
        require(record.get('horizon_kind') == 'trading_sessions', 'unsupported_horizon_kind')
        require(type(record.get('horizon_count')) is int and record['horizon_count'] > 0,
                'positive_integer_horizon_required')
        for field in ('forecast_id', 'ledger_revision', 'listing_id', 'ticker'):
            _text(record.get(field), field)

        fixtures = _mapping(fixtures, 'fixtures')
        for kind in ('ledger', 'instruments', 'calendar'):
            fixture = _mapping(fixtures.get(kind), kind + '_fixture')
            require(fixture.get('synthetic') is True, kind + '_fixture_not_synthetic')
            _text(fixture.get('version'), kind + '_version')
            require(record.get(kind + '_version') == fixture['version'], kind + '_version_mismatch')
        ledger = fixtures['ledger']
        require(ledger.get('revision') == record['ledger_revision'], 'ledger_revision_mismatch')
        bindings = _mapping(ledger.get('forecasts'), 'ledger_forecasts')
        binding = _mapping(bindings.get(record['forecast_id']), 'forecast_binding')
        for field in BINDING_FIELDS:
            require(field in binding and binding[field] == record.get(field), 'ledger_binding:' + field)
        require(isinstance(binding.get('reference_metadata'), dict) and
                binding['reference_metadata'] == record.get('reference'), 'ledger_binding:reference_metadata')

        instruments, calendar = fixtures['instruments'], fixtures['calendar']
        require(record.get('mic_version') == instruments.get('mic_version') == calendar.get('mic_version')
                and isinstance(record.get('mic_version'), str) and bool(record['mic_version']),
                'mic_version_mismatch')
        calendar_mic = _text(calendar.get('mic'), 'calendar_mic')
        require(bool(re.fullmatch(r'[A-Z0-9]{4}', calendar_mic)), 'invalid_calendar_mic')
        zone_name = _text(calendar.get('timezone'), 'calendar_timezone')
        try:
            zone = ZoneInfo(zone_name)
        except ZoneInfoNotFoundError:
            raise ValueError('calendar_timezone:unknown') from None
        start = _day(calendar.get('coverage_start'), 'coverage_start')
        end = _day(calendar.get('coverage_end'), 'coverage_end')
        require(start <= reference_day < target_day <= end, 'calendar_coverage_gap')
        require(calendar.get('complete') is True, 'calendar_not_declared_complete')
        sessions = _mapping(calendar.get('sessions'), 'sessions')
        parsed_sessions = {}
        for session_day, session in sorted(sessions.items()):
            day = _day(session_day, 'calendar_session')
            session = _mapping(session, 'calendar_session')
            close = _instant(session.get('close_at'), 'calendar_close', utc=True)
            require(start <= day <= end, 'session_outside_calendar_coverage')
            require(close.astimezone(zone).date() == day, 'session_local_date_mismatch')
            require(session.get('close_kind') == 'final_regular_session_close', 'calendar_close_not_final')
            parsed_sessions[day] = close
        require(reference_day in parsed_sessions, 'reference_not_trading_session')
        require(target_day in parsed_sessions, 'target_not_trading_session')
        count = sum(reference_day < day <= target_day for day in parsed_sessions)
        require(count == record['horizon_count'], 'horizon_count_mismatch')
        if target_day in parsed_sessions:
            target_close = parsed_sessions[target_day]
            result['maturity'] = 'pending' if now < target_close else 'mature'
            require(now >= target_close, 'target_not_mature')
            require(cutoff < target_close, 'forecast_not_before_target_close')

        listings = instruments.get('listings')
        if not isinstance(listings, list):
            raise ValueError('listings:list_required')
        endpoints = {}
        for name, day in (('reference', reference_day), ('actual', target_day)):
            endpoint = _mapping(record.get(name), name)
            endpoints[name] = endpoint
            for field in ('listing_id', 'ticker', 'mic', 'currency') + SEMANTICS:
                _text(endpoint.get(field), name + '.' + field)
            require(endpoint['listing_id'] == record['listing_id'] and endpoint['ticker'] == record['ticker'],
                    name + ':listing_identity_mismatch')
            matches = []
            for listing in listings:
                listing = _mapping(listing, 'listing')
                effective_from = _day(listing.get('effective_from'), 'effective_from')
                effective_to = _day(listing.get('effective_to'), 'effective_to')
                require(effective_from < effective_to, 'invalid_listing_interval')
                if listing.get('listing_id') == endpoint['listing_id'] and effective_from <= day < effective_to:
                    matches.append(listing)
            require(len(matches) == 1, name + ':effective_listing_not_unique')
            if len(matches) == 1:
                listing = matches[0]
                for field in ('ticker', 'mic', 'currency'):
                    require(endpoint[field] == listing.get(field), name + ':' + field + '_mapping_mismatch')
                require(listing.get('market') == 'US', name + ':listing_not_us')
            require(endpoint['mic'] == calendar_mic, name + ':calendar_mic_mismatch')
            require(endpoint.get('session_date') == day.isoformat(), name + ':session_date_mismatch')
            require(endpoint.get('session_timezone') == zone_name, name + ':session_timezone_mismatch')
            require(endpoint['source_class'] in SOURCE_CLASSES, name + ':unsupported_source_class')
            require(endpoint.get('source_claim') == 'simulated', name + ':source_claim_not_simulated')
            require(endpoint['observation_kind'] == 'final_regular_session_close', name + ':nonfinal_observation')
            require(endpoint['price_field'] == 'close', name + ':unsupported_price_field')
            require(endpoint['adjustment_basis'] in ADJUSTMENTS, name + ':unknown_adjustment_basis')
            require(endpoint['corporate_action_treatment'] not in {'unknown', 'unspecified'},
                    name + ':unknown_corporate_action_treatment')
            require(endpoint.get('value_semantics') == ('total_return_series' if endpoint['adjustment_basis'] ==
                    'total_return_adjusted' else 'traded_close_series'), name + ':value_semantics_mismatch')
            close = _instant(endpoint.get('close_at'), name + '.close_at', utc=True)
            require(day in parsed_sessions and close == parsed_sessions.get(day), name + ':session_close_mismatch')
            observed = _instant(endpoint.get('observed_at'), name + '.observed_at')
            require(observed == close, name + ':observation_not_at_final_close')
            retrieved = _instant(endpoint.get('retrieved_at'), name + '.retrieved_at')
            available_value = endpoint.get('available_at')
            if available_value is None:
                require(endpoint.get('availability_status') == 'unknown' and
                        endpoint.get('availability_fallback') == 'none', name + ':unknown_availability_declaration_missing')
                reasons.add(name + ':availability_unknown')
            else:
                require(endpoint.get('availability_status') == 'known' and
                        endpoint.get('availability_fallback') == 'none', name + ':availability_declaration_mismatch')
                available = _instant(available_value, name + '.available_at')
                require(observed <= available <= retrieved, name + ':source_time_order_invalid')
                require(available <= (cutoff if name == 'reference' else now), name + ':availability_after_boundary')
            require(observed <= retrieved, name + ':retrieval_before_observation')
            boundary = cutoff if name == 'reference' else now
            require(close <= boundary and observed <= boundary and retrieved <= boundary,
                    name + ':timestamp_after_boundary')

        for field in ('mic', 'currency') + SEMANTICS + ('value_semantics',):
            require(endpoints['reference'].get(field) == endpoints['actual'].get(field),
                    'endpoint_semantics_mismatch:' + field)

        evidence_id = _text(record.get('evidence_fixture_id'), 'evidence_fixture_id')
        evidence = _mapping(fixtures.get('evidence'), 'evidence').get(evidence_id)
        if not isinstance(evidence, bytes):
            raise ValueError('evidence_fixture_bytes_missing')
        require(hashlib.sha256(evidence).hexdigest() == record.get('evidence_sha256'), 'evidence_digest_mismatch')
        try:
            def unique_object(pairs):
                obj = {}
                for key, value in pairs:
                    if key in obj:
                        raise ValueError('duplicate_evidence_key')
                    obj[key] = value
                return obj
            def reject_constant(value):
                raise ValueError('nonfinite_evidence_constant')
            payload = json.loads(evidence, object_pairs_hook=unique_object, parse_constant=reject_constant)
        except (ValueError, UnicodeError, RecursionError):
            raise ValueError('evidence_fixture_invalid_json') from None
        expected = dict(schema_version=2, synthetic=True, forecast_id=record['forecast_id'],
                        ledger_revision=record['ledger_revision'], reference=endpoints['reference'],
                        actual=endpoints['actual'])
        require(payload == expected, 'evidence_metadata_mismatch')
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        # Stable schema failures do not expose input contents or private payloads.
        reasons.add(str(exc) if isinstance(exc, ValueError) else 'malformed_input')
    provenance_reasons = reasons - {'rights_not_synthetic_only', 'human_review_not_requested', 'target_not_mature'}
    if not provenance_reasons:
        result['provenance_status'] = 'synthetic_consistent'
    if not reasons:
        result['assessment_status'] = 'ready_for_human_review'
    return dict(result, reasons=sorted(reasons))
