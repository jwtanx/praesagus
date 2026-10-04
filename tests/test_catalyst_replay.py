"""Authored synthetic evidence only; no market, causal or model claims."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from harness.catalyst_replay import replay_cases


def news(identity='news-1', **changes):
    item = dict(news_id=identity, source_url='https://example.invalid/source', source='Synthetic disclosure',
                provider='Synthetic provider', provenance_ref='fixture:raw-1', event_cluster_id='cluster-1',
                revision_id='original', published_at='2026-10-01T10:00:00+02:00',
                provider_available_at='2026-10-01T08:05:00Z', first_observed_at='2026-10-01T08:06:00Z',
                ingested_at='2026-10-01T08:07:00Z', timestamp_precision='timestamp',
                annotation_label='plausible_catalyst')
    item.update(changes)
    return item


def case(identity='case-1', **changes):
    item = dict(case_id=identity, instrument='SYNTH-1', venue='TEST-US', currency='USD',
                event_cluster_id=identity+'-cluster', split='train', information_cutoff='2026-10-01T12:00:00Z',
                outcome_start='2026-10-01T13:00:00Z', outcome_end='2026-10-01T14:00:00Z', news=[news()])
    item.update(changes)
    return item


def envelope(cases=None, **changes):
    item = dict(schema_version=1, origin='synthetic', decision_cutoff='2026-10-01T12:00:00Z',
                review_at='2026-10-01T20:00:00Z', cases=[case()] if cases is None else cases)
    item.update(changes)
    return item


def evidence(result, index=0, item=0):
    return result['cases'][index]['news'][item]


def test_eight_controls_revisions_annotations_and_denominators_without_mutation():
    unknown = {field: None for field in ('published_at', 'provider_available_at', 'first_observed_at', 'ingested_at')}
    rows = [case('on-time'), case('no-news', news=[]), case('unknown', news=[news(**unknown, timestamp_precision='unknown', annotation_label='unknown')]),
            case('date-only', news=[news(**unknown, timestamp_precision='date')]),
            case('later-observed', news=[news(first_observed_at='2026-10-01T13:00:00Z', ingested_at='2026-10-01T14:00:00Z')]),
            case('correction', news=[news(), news('correction', revision_id='corrected', published_at='2026-10-01T13:00:00Z',
                 provider_available_at='2026-10-01T14:00:00Z', first_observed_at='2026-10-01T15:00:00Z', ingested_at='2026-10-01T16:00:00Z')]),
            case('contradictory', news=[news(annotation_label='contradictory')]),
            case('after-review', news=[news(ingested_at='2026-10-02T00:00:00Z')], outcome_end='2026-10-03T00:00:00Z')]
    rows[0]['metrics'] = {'close_return': -0.03, 'unrated': None}
    rows[0]['result_ref'] = {'id': 'fixture:uncomputed'}
    data = envelope(rows)
    before = deepcopy(data)
    result = replay_cases(data)
    assert data == before and [entry['case'] for entry in result['cases']] == rows
    assert all(entry['prospective_eligible'] for entry in result['cases']), 'Case timing is separate from news availability'
    assert evidence(result)['evidence']['published_at'] == '2026-10-01T10:00:00+02:00'
    assert evidence(result, 2)['availability'] == 'unavailable'
    assert 'published_at_unknown' in evidence(result, 2)['reason_codes']
    assert 'timestamp_precision_date' in evidence(result, 3)['reason_codes']
    assert evidence(result, 4)['availability'] == 'explanation_only'
    assert 'first_observed_at_after_information_cutoff' in evidence(result, 4)['reason_codes']
    assert evidence(result, 5)['prospective_eligible'] and evidence(result, 5, 1)['availability'] == 'explanation_only'
    assert evidence(result, 6)['prospective_eligible'], 'Contradictory annotation is not contradictory timestamps'
    assert evidence(result, 7)['availability'] == 'unavailable'
    assert 'ingested_at_after_review_at' in evidence(result, 7)['reason_codes']
    assert result['cases'][7]['outcome_status'] == 'pending'
    summary = result['summary']
    assert summary['case_count'] == 8 and summary['empty_news_case_count'] == 1
    assert summary['news_count'] == 8 and summary['prospective_eligible_news_count'] == 3
    assert summary['prospective_excluded_news_count'] == 5 and summary['explanation_only_news_count'] == 2
    assert summary['unavailable_news_count'] == 3 and summary['pending_outcome_case_count'] == 1
    assert summary['unique_cluster_id_count'] == 9 and summary['connected_component_count'] == 2
    result['cases'][0]['case']['metrics']['close_return'] = 99
    evidence(result)['evidence']['provider'] = 'changed'
    assert data == before, 'Output mutations cannot change input evidence'


def test_cutoff_boundary_precision_and_offsets_are_instants_not_exchange_inference():
    item = news(published_at='2026-10-01T14:00:00+02:00', provider_available_at='2026-10-01T12:00:00Z',
                first_observed_at='2026-10-01T08:00:00-04:00', ingested_at='2026-10-01T12:00:00+00:00')
    result = replay_cases(envelope([case(news=[item], outcome_start='2026-10-01T13:00:00Z', outcome_end='2026-10-01T13:00:00Z')]))
    assert evidence(result)['prospective_eligible'] and evidence(result)['reason_codes'] == []
    assert evidence(result)['evidence'] == item
    assert 'auction' not in str(result)


def test_contradictory_timestamp_order_cannot_be_explanation_only():
    result = replay_cases(envelope([case(news=[news(provider_available_at='2026-10-01T07:00:00Z')])]))
    row = evidence(result)
    assert row['availability'] == 'unavailable' and not row['prospective_eligible']
    assert 'timestamp_order_published_at_provider_available_at' in row['reason_codes']


def split_case(identity, split, day, **changes):
    return case(identity, split=split, information_cutoff=f'2026-09-{day:02}T12:00:00Z',
                outcome_start=f'2026-09-{day:02}T13:00:00Z', outcome_end=f'2026-09-{day+1:02}T12:00:00Z', news=[], **changes)


def test_temporal_fold_boundaries_exact_label_availability_and_absent_splits():
    rows = [split_case('train', 'train', 1), split_case('calibration', 'calibration', 2), split_case('test', 'test', 3)]
    result = replay_cases(envelope(rows))
    assert result['folds_valid'] and result['violations'] == [], 'Outcome equality at fitting cutoff is available'
    assert replay_cases(envelope([rows[0], rows[2]]))['folds_valid']
    assert replay_cases(envelope([]))['summary'] == {
        'case_count': 0, 'prospective_eligible_case_count': 0, 'prospective_excluded_case_count': 0,
        'empty_news_case_count': 0, 'news_count': 0, 'prospective_eligible_news_count': 0,
        'prospective_excluded_news_count': 0, 'explanation_only_news_count': 0, 'unavailable_news_count': 0,
        'unique_cluster_id_count': 0, 'connected_component_count': 0, 'pending_outcome_case_count': 0}


def test_transitive_clusters_include_ineligible_links_and_preserve_all_cases():
    rows = [split_case('a', 'train', 1), split_case('b', 'train', 1), split_case('c', 'test', 3)]
    rows[0].update(event_cluster_id='A', news=[news(event_cluster_id='B')])
    rows[1].update(event_cluster_id='B', news=[news(event_cluster_id='C')])
    rows[2].update(event_cluster_id='C', news=[news(event_cluster_id='D', ingested_at='2099-01-01T00:00:00Z')])
    result = replay_cases(envelope(rows))
    assert not result['folds_valid'] and len(result['cases']) == 3
    assert result['summary']['unique_cluster_id_count'] == 4 and result['summary']['connected_component_count'] == 1
    violation = next(v for v in result['violations'] if v['code'] == 'cluster_crosses_splits')
    assert violation['case_ids'] == ['a', 'b', 'c'] and violation['splits'] == ['train', 'test']
    assert all(not row['prospective_eligible'] for entry in result['cases'] for row in entry['news'])


def test_fold_checks_use_earliest_later_cutoff_and_distinguish_overlap_from_unavailable():
    early = split_case('train', 'train', 1)
    late = split_case('cal', 'calibration', 2)
    later = split_case('cal-later', 'calibration', 4)
    early['outcome_end'] = '2026-09-03T00:00:00Z'
    result = replay_cases(envelope([early, later, late]))
    codes = {v['code'] for v in result['violations']}
    assert codes == {'outcome_unavailable_at_fitting_cutoff', 'outcome_overlaps_fitting_cutoff'}
    assert all(v['later_case_ids'] == ['cal'] for v in result['violations'])
    early['outcome_start'] = '2026-09-02T13:00:00Z'
    result = replay_cases(envelope([early, late]))
    assert [v['code'] for v in result['violations']] == ['outcome_unavailable_at_fitting_cutoff']
    early.update(information_cutoff=late['information_cutoff'], outcome_start='2026-09-02T13:00:00Z')
    assert 'split_cutoff_order' in {v['code'] for v in replay_cases(envelope([early, late]))['violations']}


@pytest.mark.parametrize('field,value', [('schema_version', True), ('schema_version', 2), ('origin', 'provider'),
    ('decision_cutoff', '2026-10-01'), ('decision_cutoff', '2026-10-01T12:00:00'),
    ('review_at', '2026-09-30T00:00:00Z'), ('cases', None)])
def test_reject_malformed_envelope(field, value):
    data = envelope()
    data[field] = value
    with pytest.raises(ValueError):
        replay_cases(data)


@pytest.mark.parametrize('field,value', [('case_id', ''), ('instrument', None), ('split', 'future'),
    ('information_cutoff', '2026-10-01T13:00:00Z'), ('information_cutoff', 'bad'),
    ('outcome_start', '2026-10-01T12:00:00Z'), ('outcome_end', '2026-10-01T12:00:00Z'), ('news', None)])
def test_reject_malformed_case(field, value):
    data = envelope()
    data['cases'][0][field] = value
    with pytest.raises(ValueError):
        replay_cases(data)


@pytest.mark.parametrize('url', ['javascript:evil', 'https://user:pass@example.invalid', 'https://@example.invalid',
    '//example.invalid', 'https://example.invalid:bad', 'https://example.invalid:65536',
    'https://example.invalid/\nevil', 'https://example.invalid/\x7f', 'https://example.invalid/\\evil'])
def test_reject_unsafe_urls(url):
    with pytest.raises(ValueError):
        replay_cases(envelope([case(news=[news(source_url=url)])]))


@pytest.mark.parametrize('field,value', [('news_id', ''), ('source', None), ('provider', ''), ('provenance_ref', ''),
    ('event_cluster_id', None), ('revision_id', ''), ('annotation_label', 'caused_price_move'),
    ('timestamp_precision', 'minute'), ('published_at', '2026-10-01'), ('ingested_at', '2026-10-01T10:00:00')])
def test_reject_malformed_news(field, value):
    item = news()
    item[field] = value
    with pytest.raises(ValueError):
        replay_cases(envelope([case(news=[item])]))


def test_explicit_null_required_and_duplicate_identity_rejection():
    item = news()
    del item['first_observed_at']
    with pytest.raises(ValueError, match='explicit null'):
        replay_cases(envelope([case(news=[item])]))
    with pytest.raises(ValueError, match='duplicate case_id'):
        replay_cases(envelope([case(), case()]))
    with pytest.raises(ValueError, match='duplicate per-case news_id'):
        replay_cases(envelope([case(news=[news(), news(revision_id='changed')])]))
    assert replay_cases(envelope([case('a'), case('b')]))['summary']['news_count'] == 2


def test_pure_replay_has_no_file_or_socket_lookup():
    with patch('builtins.open', side_effect=AssertionError('file read')), patch('socket.socket', side_effect=AssertionError('network')):
        assert replay_cases(envelope())['cases'][0]['prospective_eligible']


def test_long_transitive_component_uses_bounded_stack_and_retains_future_links():
    items = [news(str(index), event_cluster_id=f'c{2000-index:04}', ingested_at='2099-01-01T00:00:00Z')
             for index in range(1200)]
    data = envelope([case('a', event_cluster_id='z', news=items), case('b', event_cluster_id='c2000', news=[])])
    result = replay_cases(data)
    assert result['summary']['news_count'] == 1200
    assert result['summary']['unique_cluster_id_count'] == 1201
    assert result['summary']['connected_component_count'] == 1
    assert result['summary']['prospective_excluded_news_count'] == 1200
    assert result['folds_valid']


@pytest.mark.parametrize('label', ['plausible_catalyst', 'context_correlation', 'contradictory', 'unknown'])
def test_all_authored_labels_remain_annotations_not_eligibility_inputs(label):
    assert evidence(replay_cases(envelope([case(news=[news(annotation_label=label)])])))['prospective_eligible']


def test_review_and_outcome_references_do_not_select_prospective_inputs():
    data = envelope([case(news=[news(ingested_at='2026-10-02T00:00:00Z')],
                          outcome_end='2026-10-03T00:00:00Z', metrics={'return': 999},
                          result_ref={'outcome': 'caller-authored'})])
    before = replay_cases(data)
    data['review_at'] = '2026-10-04T00:00:00Z'
    data['cases'][0]['metrics']['return'] = -999
    after = replay_cases(data)
    assert not evidence(before)['prospective_eligible'] and not evidence(after)['prospective_eligible']
    assert evidence(before)['availability'] == 'unavailable' and evidence(after)['availability'] == 'explanation_only'
    assert before['cases'][0]['outcome_status'] == 'pending' and after['cases'][0]['outcome_status'] == 'available'
    assert after['cases'][0]['case']['result_ref'] == data['cases'][0]['result_ref']
    item = news(provider_available_at=None, first_observed_at='2026-10-01T07:00:00Z')
    row = evidence(replay_cases(envelope([case(news=[item])])))
    assert 'provider_available_at_unknown' in row['reason_codes']
    assert 'timestamp_order_published_at_first_observed_at' in row['reason_codes']
