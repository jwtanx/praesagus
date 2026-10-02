"""Versioned report contract tests independent of live report content/providers."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts/daily-market-brief'
sys.path.insert(0, str(SCRIPT_DIR))
spec = importlib.util.spec_from_file_location('report_validator', SCRIPT_DIR / 'validate_report_json.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
sys.path.pop(0)


@pytest.fixture
def report(tmp_path):
    folder = tmp_path / 'daily-market-brief'
    folder.mkdir()
    shared = tmp_path / 'financial-calendar'
    shared.mkdir()
    (shared / '2026-10.json').write_text(json.dumps({'schema_version': 1, 'month': '2026-10',
        'timezone': 'Asia/Kuala_Lumpur', 'notes': [], 'entries': []}))
    groups = [{'key': key, 'label': key, 'emoji': 'S'} for key in ('technology', 'semiconductors')]
    rows = []
    for group in groups:
        for n in range(5):
            row = dict(market='US', country='us', asset_type='equity', ticker=group['key']+str(n), name='Fixture',
                sector=group['label'], sector_category=group['key'], sector_emoji='S', currency='USD',
                current_price='USD 10', price_as_of='2026-10-01T08:00:00+08:00', direction='unknown',
                direction_label='Unknown', estimated_mid_case='Unavailable', estimated_range='Unavailable',
                scenario='Research only', current_price_value=10, estimated_mid_case_value=None,
                range_low_value=None, range_high_value=None, forecast_status='unavailable',
                quote_status='observed', data_gaps=['No validated target'], confidence='unavailable',
                confidence_reason='No forecast method evidence', sources=[])
            rows.append(row)
    data = dict(schema_version=3, metadata={'date': '2026-10-01', 'title': 'Fixture', 'subtitle': 'Fixture',
        'as_of': '2026-10-01T08:00:00+08:00'}, summary=[{'label': 'Fixture', 'title': 'Fixture', 'summary': 'Fixture'}],
        sections={key: {'title': key, 'kicker': key, 'description': [], 'tables': [], 'items': [], 'notes': []}
            for key in validator.REQUIRED_SECTIONS-{'calendar'}},
        watchlist_config={'count_per_group': 5, 'groups': groups}, forecasts=rows,
        calendar_ref='../financial-calendar/2026-10.json', footer='Research only')
    return folder / '2026-10-01.json', data


def test_five_name_shared_calendar(report):
    path, data = report
    assert validator.validate_report(path, data)[:2] == (10, 0)


@pytest.mark.parametrize('change', ['count', 'inline', 'confidence', 'reason', 'unknown_target', 'bad_ref', 'missing_calendar'])
def test_reject_bad_contract(report, change):
    path, data = report
    if change == 'count':
        data['forecasts'].pop()
    elif change == 'inline':
        data['calendar'] = {'events': []}
    elif change == 'confidence':
        data['forecasts'][0]['confidence'] = '90%'
    elif change == 'reason':
        data['forecasts'][0]['confidence_reason'] = ''
    elif change == 'unknown_target':
        data['forecasts'][0]['estimated_mid_case_value'] = 100
    elif change == 'bad_ref':
        data['calendar_ref'] = '../../private.json'
    else:
        (path.parent / data['calendar_ref']).unlink()
    with pytest.raises(ValueError):
        validator.validate_report(path, data)


def observed_point(cutoff):
    return dict(price=10,volume=0,source_at='2026-09-30T23:59:00Z',observed_at='2026-09-30T23:59:00Z',
        ingested_at='2026-10-01T00:00:00Z',known_at='2026-10-01T00:00:00Z',cutoff=cutoff,
        origin='synthetic',currency=None,session=None,adjustment=None,prior_close=None,
        gaps=['currency_unknown','session_unknown','adjustment_unknown','prior_close_unknown'],
        provenance=dict(provider='moomoo-rest',connector='moomoo-rest-capture',capture_authenticity='caller-supplied-unverified',
            rights_status='unconfirmed',attempt_id='a'*64,raw_hash='b'*64,semantic_hash='c'*64,run_id='synthetic'))


def test_optional_observed_quote_preserves_legacy_contract(report):
    path,data=report;row=data['forecasts'][0]
    row.update(observed_quote=observed_point(data['metadata']['as_of']),current_price_value=None,quote_status='missing')
    assert validator.validate_report(path,data)[:2]==(10,0)


@pytest.mark.parametrize('change',['sortable','currency','forecast','precision','future','raw','account','missing-gap','known-order'])
def test_invalid_observed_quote_rejected(report,change):
    path,data=report;row=data['forecasts'][0]
    row.update(observed_quote=observed_point(data['metadata']['as_of']),current_price_value=None,quote_status='missing')
    q=row['observed_quote']
    if change=='sortable':row['current_price_value']=10
    elif change=='currency':q['currency']='USD'
    elif change=='forecast':row['direction']='up'
    elif change=='precision':q['source_at']='2026-09-30T23:59:00.1234567Z'
    elif change=='future':q['ingested_at']='2026-10-01T00:00:01Z'
    elif change=='raw':q['raw_body']='private'
    elif change=='account':q['provenance']['account_id']='private'
    elif change=='missing-gap':q['gaps']=[]
    else:q['known_at']='2026-09-30T23:59:00Z'
    with pytest.raises(ValueError):validator.validate_report(path,data)
