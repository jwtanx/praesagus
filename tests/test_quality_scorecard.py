"""Fictional immutable forecasts/actuals only; no prediction, fitting or transport."""
import copy
import csv
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/stock-research'
sys.path.insert(0, str(SCRIPT))
spec = importlib.util.spec_from_file_location('quality_scorecard', SCRIPT/'quality_scorecard.py')
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
NOW = datetime(2026, 10, 30, tzinfo=timezone.utc)


class Fixture:
    def __init__(self):
        self.files = {}

    def put(self, name, value):
        raw = value if isinstance(value, bytes) else q.canonical(value)
        path = '/fictional/'+name
        self.files[path] = raw
        return dict(path=path, sha256=q.sha(raw), bytes=len(raw))

    def replace(self, ref, value):
        return self.put(Path(ref['path']).name, value)

    def snapshots(self):
        return q.Snapshots(reader=lambda p:self.files[p])


def csv_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=sorted(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def financial(analysis, analysis_sha, cohort, reviews):
    return dict(schema_version=1, kind='quality-scorecard-financial-review', reviewer='Trader',
        analysis_sha256=analysis_sha, reviewed_at='2026-10-22T06:00:00+00:00', decision='accepted',
        cohorts=[dict(cohort_id=cohort['cohort_id'], forecasts_sha256=cohort['forecasts']['sha256'],
            target_semantics='terminal_close' if cohort['kind']=='terminal_close_csv' else 'whole_window_ohlc',
            accepted_outcome_review_sha256=[r['sha256'] for r in reviews], limitations=['Fictional'])],
        limitations=['Fictional, no promotion'])


def terminal_fixture(*, actual=True, original_changes=None, review_changes=None, withheld=False):
    f = Fixture()
    evidence = dict(instrument=dict(instrument_id='US.DEMO', currency='USD'), method={'method_id':'fictional'},
                    source=dict(basis='unadjusted', source_field='close', estimand='vendor_regular_close'))
    admission = dict(fictional=True)
    original = {k:'' for k in q.EXPORT_COLUMNS}
    original.update(purpose='private_research_only', ticker='DEMO', market='US', currency='USD',
        status='withheld' if withheld else 'generated', classification='reviewed_real', is_demo='False',
        reference_session='2026-10-19', reference_close_at='2026-10-19T20:00:00Z', reference_close='100',
        target_session='2026-10-20', target_close_at='2026-10-20T20:00:00Z',
        issued_at='2026-10-20T10:00:00Z', report_cutoff='2026-10-20T10:00:00Z',
        point='105', low='95', high='110', direction='up', horizon_sessions='1', method_id='fictional',
        range_scope='next_close_not_intraday_extrema_no_measured_95pct_coverage',
        source_url='https://example.test/close', evidence_sha256=q.sha(q.canonical(evidence)),
        admission_sha256=q.sha(q.canonical(admission)), result_sha256='c'*64)
    original.update(original_changes or {})
    forecasts = f.put('forecasts.csv', csv_bytes([original]))
    known = q.milliseconds('2026-10-21T04:00:00Z')
    review = dict(ticker='DEMO', market='US', reviewer='Trader', reviewed_at='2026-10-21T05:00:00Z',
        decision='accepted_private_outcome_comparability', failures=[], checks={k:True for k in q.CHECKS},
        frozen_csv_sha256=forecasts['sha256'], frozen_row_sha256=q.sha(q.canonical(original)),
        frozen_evidence_sha256=original['evidence_sha256'], frozen_admission_sha256=original['admission_sha256'],
        frozen_result_sha256=original['result_sha256'], actual_close=108., actual_session='2026-10-20',
        actual_currency='USD', actual_basis='unadjusted', actual_source_field='close',
        actual_source_url='https://example.test/close', actual_available_at='2026-10-21T04:00:00Z',
        actual_settled_at='2026-10-21T00:00:00Z', actual_raw_hash='a'*64, actual_semantic_hash='b'*64,
        actual_store_binding=dict(record=dict(code='US.DEMO', date='2026-10-20', adjustment=0, close=108.),
            semantic_hash='b'*64, observation=dict(known_ms=known, ingested_ms=known,
                observed_ms=known-1, raw_hash='a'*64, status='success')))
    review.update(review_changes or {})
    reviews = [f.put('actual.json', review)] if actual else []
    cohort = dict(cohort_id='terminal', kind='terminal_close_csv', forecasts=forecasts,
        original_batch=f.put('batch.json', dict(items=[dict(market='US', ticker='DEMO',
                                                        evidence=evidence, admission=admission)])),
        outcome_reviews=reviews, outcome_acceptance=f.put('acceptance.json',dict(status='accepted_privateonly',
            original_forecasts_preserved=True, outcome_comparability=len(reviews), at='2026-10-21T05:00:00Z')),
        baseline=None)
    analysis = dict(schema_version=1, review_at='2026-10-21T06:00:00Z', qualification_policy=None, cohorts=[cohort])
    a_ref = f.put('analysis.json', analysis)
    domain = financial(analysis, a_ref['sha256'], cohort, reviews)
    return f, analysis, a_ref, domain, original, review


def score(f, analysis, ref, domain):
    return q.build_scorecard(analysis, ref['sha256'], domain, f.snapshots(), workflow_now=NOW)


def test_terminal_reuses_review_and_keeps_target_semantics():
    f,a,r,d,_,_ = terminal_fixture()
    before = dict(f.files)
    result = score(f,a,r,d)
    row = result['rows'][0]
    assert row['scoring_status']=='scored' and row['quality_status']=='insufficient'
    assert row['point_absolute_error']==3 and row['point_error_fraction']==.03
    assert row['terminal_range_hit'] is True and row['direction_hit'] is True
    assert row['terminal_range_width']==15
    assert row['low_endpoint_error'] is None and row['whole_window_containment'] is None
    assert row['baseline_comparison'] is None and row['baseline_available'] is False
    assert result['summary']['terminal_close']['scored_origin_dates']==1
    assert f.files==before


@pytest.mark.parametrize('changes,reason', [
    ({'actual_currency':'MYR'}, 'actual-target-currency-basis-identity'),
    ({'actual_session':'2026-10-19'}, 'actual-target-currency-basis-identity'),
    ({'actual_basis':'adjusted'}, 'actual-target-currency-basis-identity'),
    ({'actual_source_field':'snapshot'}, 'actual-target-currency-basis-identity'),
    ({'actual_available_at':'2026-10-22T04:00:00Z'}, 'actual-availability-or-settlement'),
    ({'actual_settled_at':'2026-10-20T19:00:00Z'}, 'actual-availability-or-settlement'),
    ({'reviewed_at':'2026-10-22T05:00:00Z'}, 'actual-review-after-cutoff'),
    ({'frozen_row_sha256':'d'*64}, 'original-forecast-binding-mismatch'),
    ({'frozen_csv_sha256':'d'*64}, 'original-forecast-binding-mismatch'),
    ({'frozen_result_sha256':'d'*64}, 'original-forecast-binding-mismatch'),
    ({'decision':'approved', 'approved':True}, 'outcome-comparability-not-accepted'),
    ({'actual_close':float('inf')}, 'invalid-positive-number'),
])
def test_rejected_actuals_do_not_score(changes, reason):
    if changes.get('actual_close')==float('inf'):
        # JSON nonfinite input is rejected at the snapshot boundary instead.
        with pytest.raises(ValueError):terminal_fixture(review_changes=changes)
        return
    f,a,r,d,_,_ = terminal_fixture(review_changes=changes)
    row = score(f,a,r,d)['rows'][0]
    assert row['quality_status']=='failed' and reason in row['reasons'][0]
    assert row['point_absolute_error'] is None


def test_true_approval_cannot_override_failed_comparability():
    f,a,r,d,_,rev = terminal_fixture()
    rev['checks']['original_actions_cover_outcome']=False
    a['cohorts'][0]['outcome_reviews']=[f.replace(a['cohorts'][0]['outcome_reviews'][0],rev)]
    d['cohorts'][0]['accepted_outcome_review_sha256']=[a['cohorts'][0]['outcome_reviews'][0]['sha256']]
    assert score(f,a,r,d)['rows'][0]['scoring_status']=='invalid'


def test_missing_actual_and_withheld_are_visible():
    f,a,r,d,_,_ = terminal_fixture(actual=False)
    assert score(f,a,r,d)['rows'][0]['scoring_status']=='missing_actual'
    f,a,r,d,_,_ = terminal_fixture(withheld=True)
    assert score(f,a,r,d)['rows'][0]['scoring_status']=='withheld'


def test_terminal_pending_never_scores_even_if_later_actual_supplied():
    f,a,r,d,_,_ = terminal_fixture()
    a['review_at']='2026-10-20T19:00:00Z'
    # Retained root review itself was not known by this cutoff; cannot borrow it.
    with pytest.raises(ValueError, match='acceptance-missing'):score(f,a,r,d)


@pytest.mark.parametrize('original_changes', [
    {'issued_at':'2026-10-22T00:00:00Z'}, {'target_close_at':'2026-10-20T09:00:00Z'},
    {'range_scope':'intraday_high_low'}, {'horizon_sessions':'5'}, {'is_demo':'True'},
    {'point':'nan'}, {'low':'111'}, {'ticker':'=FORMULA'}, {'status':'unknown-but-hash-consistent'},
])
def test_bad_originals_are_failed_rows(original_changes):
    f,a,r,d,_,_ = terminal_fixture(original_changes=original_changes)
    assert score(f,a,r,d)['rows'][0]['quality_status']=='failed'


def test_duplicate_and_conflicting_actuals_rejected():
    f,a,r,d,_,rev = terminal_fixture()
    second = copy.deepcopy(rev);second['actual_close']=109
    a['cohorts'][0]['outcome_reviews'].append(f.put('conflicting.json',second))
    d['cohorts'][0]['accepted_outcome_review_sha256'].append(a['cohorts'][0]['outcome_reviews'][-1]['sha256'])
    acceptance=a['cohorts'][0]['outcome_acceptance']
    a['cohorts'][0]['outcome_acceptance']=f.replace(acceptance,dict(status='accepted_privateonly',
        original_forecasts_preserved=True,outcome_comparability=2,at='2026-10-21T05:00:00Z'))
    row=score(f,a,r,d)['rows'][0]
    assert row['scoring_status']=='invalid' and row['reasons']==['duplicate-or-conflicting-actual-reviews']


def test_duplicate_original_issuances_not_counted_twice():
    f,a,r,d,original,rev = terminal_fixture()
    c=a['cohorts'][0];c['forecasts']=f.replace(c['forecasts'],csv_bytes([original,original]))
    rev['frozen_csv_sha256']=c['forecasts']['sha256'];c['outcome_reviews']=[f.replace(c['outcome_reviews'][0],rev)]
    d['cohorts'][0].update(forecasts_sha256=c['forecasts']['sha256'],accepted_outcome_review_sha256=[c['outcome_reviews'][0]['sha256']])
    result=score(f,a,r,d)
    assert result['summary']['terminal_close']['counts']=={'invalid':2}


def test_unknown_fields_and_future_cutoff_reject():
    f,a,r,d,_,_=terminal_fixture()
    a['unknown']=True
    with pytest.raises(ValueError,match='unknown-or-missing'):score(f,a,r,d)
    a.pop('unknown');a['review_at']='2027-01-01T00:00:00Z'
    with pytest.raises(ValueError,match='future-review'):score(f,a,r,d)


def test_financial_review_cannot_bind_other_analysis_or_forecasts():
    f,a,r,d,_,_=terminal_fixture();d['analysis_sha256']='x'*64
    with pytest.raises(ValueError,match='financial-review'):score(f,a,r,d)
    d['analysis_sha256']=r['sha256'];d['cohorts'][0]['forecasts_sha256']='a'*64
    with pytest.raises(ValueError,match='financial-forecast'):score(f,a,r,d)


def test_null_policy_cannot_be_replaced_by_posthoc_threshold():
    f,a,r,d,_,_=terminal_fixture();a['qualification_policy']={'min_accuracy':0}
    with pytest.raises(ValueError,match='qualification-policy'):score(f,a,r,d)


def with_audit_baseline():
    f,a,r,d,original,review=terminal_fixture()
    c=a['cohorts'][0];batch=json.loads(f.files[c['original_batch']['path']])
    estimates=dict(point=105.004,low=95.004,high=110.004,baseline_point=104.9999,
        baseline_low=94.9999,baseline_high=109.9999,display_point=105.,display_low=95.,display_high=110.)
    origin={k:original[k] for k in ('issued_at','report_cutoff','reference_session','target_session',
                                  'method_id','reference_close_at','target_close_at','evidence_sha256','admission_sha256')}
    origin.update(reference_close=100.,horizon_sessions=1,
        method_sha256=q.sha(q.canonical(batch['items'][0]['evidence']['method'])))
    origin.update({k:v for k,v in estimates.items() if not k.startswith('display_')})
    result=dict(status='generated',classification='reviewed_real',instrument={'instrument_id':'US.DEMO',
        'currency':'USD'},estimates=estimates,provenance={'audit':origin})
    original['result_sha256']=q.sha(q.canonical(result))
    c['forecasts']=f.replace(c['forecasts'],csv_bytes([original]))
    review.update(frozen_csv_sha256=c['forecasts']['sha256'],frozen_row_sha256=q.sha(q.canonical(original)),
                  frozen_result_sha256=original['result_sha256'])
    c['outcome_reviews']=[f.replace(c['outcome_reviews'][0],review)]
    ar=f.put('audit.json',dict(issued_at=original['issued_at'],report_cutoff=original['report_cutoff'],
        input_sha256='f'*64,rows=[dict(market='US',ticker='DEMO',currency='USD',result=result,
            **{k:original[k] for k in ('evidence_sha256','admission_sha256','result_sha256')})]))
    mr=f.put('manifest.json',dict(kind='private-forecast-csv',is_demo=False,purpose='private_research_only',
        created_at='2026-10-20T10:00:00.1Z',input_sha256='f'*64,artifacts={
            'forecasts.csv':{k:c['forecasts'][k] for k in ('sha256','bytes')},
            'private-audit.json':{k:ar[k] for k in ('sha256','bytes')}}))
    c['baseline']=dict(kind='original_audit',audit=ar,manifest=mr,precision='original_unrounded_both')
    d['cohorts'][0].update(forecasts_sha256=c['forecasts']['sha256'],
        accepted_outcome_review_sha256=[x['sha256'] for x in c['outcome_reviews']])
    return f,a,r,d


def test_original_baseline_uses_same_unrounded_precision():
    f,a,r,d=with_audit_baseline();result=score(f,a,r,d);row=result['rows'][0]
    assert row['point_absolute_error']==3 # Original CSV display precision remains separate.
    assert row['model_metrics']['absolute_error']==pytest.approx(2.996)
    assert row['baseline_metrics']['absolute_error']==pytest.approx(3.0001)
    assert row['normalized_error']==pytest.approx(.03) # Display diagnostic, not the paired precision.
    assert row['baseline_comparison']['precision']=='original_unrounded_both'
    summary=result['summary']['terminal_close']['paired_comparison']
    assert summary['pairs']==1 and summary['model_smaller_absolute_error']==1
    assert row['quality_status']=='insufficient'


@pytest.mark.parametrize('change', ['identity','result_hash','issued_after','method','estimate'])
def test_bad_original_baseline_binding_preserves_actual_score(change):
    f,a,r,d=with_audit_baseline();c=a['cohorts'][0];ar=c['baseline']['audit'];audit=json.loads(f.files[ar['path']])
    row=audit['rows'][0]
    if change=='identity':row['ticker']='OTHER'
    elif change=='result_hash':row['result_sha256']='z'*64
    elif change=='issued_after':audit['issued_at']='2026-10-21T10:00:00Z'
    elif change=='method':row['result']['provenance']['audit']['method_sha256']='a'*64
    else:row['result']['estimates']['point']=1.
    c['baseline']['audit']=f.replace(ar,audit)
    mr=c['baseline']['manifest'];manifest=json.loads(f.files[mr['path']]);manifest['artifacts']['private-audit.json']={
        k:c['baseline']['audit'][k] for k in ('sha256','bytes')};c['baseline']['manifest']=f.replace(mr,manifest)
    row=score(f,a,r,d)['rows'][0]
    assert row['scoring_status']=='scored' and row['baseline_available'] is False
    assert row['point_absolute_error']==3 and any('baseline-unavailable' in x for x in row['reasons'])


def test_baseline_manifest_or_precision_override_rejects():
    f,a,r,d=with_audit_baseline();a['cohorts'][0]['baseline']['precision']='rounded-model-unrounded-baseline'
    with pytest.raises(ValueError,match='precision-contract'):score(f,a,r,d)


def test_snapshot_tampering_and_budget():
    f,a,r,d,_,_=terminal_fixture();f.files[r['path']]+=b' '
    with pytest.raises(ValueError,match='hash-or-bytes'):f.snapshots().read(r)
    with pytest.raises(ValueError,match='invalid-integer'):q.check_ref(dict(path='/test',sha256='a'*64,bytes=True))
    with pytest.raises(ValueError,match='duplicate-json'):q.decode(b'{"a":1,"a":2}')
    with pytest.raises(ValueError,match='nonfinite-json'):q.decode(b'{"a":NaN}')


def test_safe_html_and_spreadsheet_cells():
    f,a,r,d,_,_=terminal_fixture();result=score(f,a,r,d)
    result['rows'][0]['reasons']=['<script>alert(1)</script>', '=HYPERLINK("bad")']
    assert b'<script>alert(1)</script>' not in q.render_html(result) and b'&lt;script&gt;' in q.render_html(result)
    assert q.safe_cell('=bad')=="'=bad" and q.safe_cell(' @SUM(A1)')=="' @SUM(A1)"
    assert q.safe_cell(-.1)==-.1


def test_correlated_editions_and_horizons_do_not_gain_date_weight():
    rows=[]
    for instrument,origin,horizon,value in [('US.A','2026-10-19','1d',0),
        ('US.A','2026-10-19','1d',2),('US.A','2026-10-19','3d',0),
        ('US.B','2026-10-19','1d',1),('US.C','2026-10-20','1d',2)]:
        row=q.result_row('fixture',instrument,'2026-10-23',horizon,origin,'',str(len(rows)),
                         'whole_window_ohlc','USD')
        row.update(scoring_status='scored',normalized_error=value)
        rows.append(row)
    summary=q.summarize(rows)
    assert summary['metrics']['normalized_error']==pytest.approx(1.375)
    assert summary['scored_origin_dates']==2 and summary['issuances']==5


def test_paired_errors_and_rates_share_unequal_date_vintage_weighting():
    rows=[]
    cases=[('US.A','2026-10-19','1d',0,2,True),('US.A','2026-10-19','1d',2,0,False),
           ('US.A','2026-10-19','3d',0,0,True),('US.B','2026-10-19','1d',1,1,False),
           ('US.C','2026-10-20','1d',2,0,True)]
    for instrument,origin,horizon,model,baseline,coverage in cases:
        row=q.result_row('fixture',instrument,'2026-10-23',horizon,origin,'',str(len(rows)),'terminal_close','USD')
        row.update(scoring_status='scored',baseline_available=True,
            model_metrics={'absolute_error_fraction':model,'range_hit':coverage},
            baseline_metrics={'absolute_error_fraction':baseline,'range_hit':not coverage})
        rows.append(row)
    summary=q.summarize(rows)['paired_comparison']
    assert summary['model_mean_absolute_error_fraction']==pytest.approx(1.375)
    assert summary['baseline_mean_absolute_error_fraction']==pytest.approx(.375)
    assert summary['model_weighted_range_hit_rate']==pytest.approx(.6875)
    assert summary['baseline_weighted_range_hit_rate']==pytest.approx(.3125)
    assert summary['pairs']==5 and summary['model_range_hits']==3
    assert summary['distinct_origin_dates']==2 and summary['distinct_instrument_targets']==4


def test_metadata_type_and_deep_json_are_bounded():
    f,a,r,d,_,_=terminal_fixture();a['interface_notes']={'unknown':'shape'}
    with pytest.raises(ValueError,match='metadata-schema'):score(f,a,r,d)
    with pytest.raises(ValueError,match='json-nesting-budget'):q.decode(b'['*2000+b'0'+b']'*2000)


def test_html_has_readable_metrics_original_actual_controls_and_failure_denominators():
    f,a,r,d=with_audit_baseline();result=score(f,a,r,d)
    page=q.render_html(result).decode()
    for text in ('Original prediction','Actual outcome','2.9960%','3.0001%','No quality qualification',
                 'scored / mature generated targets','Download rows','Input provenance'):
        assert text in page
    for control in ('search','status','horizon','semantics'):
        assert 'id="'+control+'"' in page
    assert 'Point 105; closing interval 95–110 USD' in page and '<td>108</td>' in page
    assert "row.textContent.toLowerCase()" in page and 'innerHTML' not in page
    assert 'Content-Security-Policy' in page and 'sha256-' in page and 'default-src &#x27;none&#x27;' in page
    f,a,r,d,_,_=terminal_fixture(review_changes={'actual_currency':'MYR'})
    page=q.render_html(score(f,a,r,d)).decode()
    assert '<strong>1</strong><span>Failed input</span>' in page
    assert 'actual-target-currency-basis-identity' in page
    assert '<strong>0 / 1</strong>' in page


@pytest.fixture(scope='module')
def calendar():
    from market_calendar import MarketCalendar
    return MarketCalendar('2026-01-01','2026-12-31','XNYS')


def ohlc_fixture(calendar, *, actual=True):
    from inference import converted_quantiles
    from storage import HISTORY_COLUMNS
    f=Fixture();origin='2026-10-19';target='2026-10-20';end=calendar.close_ms(origin)
    reference=dict(session_date=origin,close=100.,currency='USD',adjustment='forward-excluding-dividends',
        known_at_ms=end+1,price_known_at_ms=end+1,retrieved_at_ms=end+1,source_at_ms=end,
        currency_known_at_ms=end+1)
    basis=dict(adjustment_vintage_id='fiction',currency='USD',adjustment='forward-excluding-dividends',
        source_hash='a'*64,known_at_ms=end)
    quantiles=converted_quantiles([[-.05,-.02,0.],[0.,.02,.05],[-.03,0.,.03]],100.)
    forecast=dict(schema_version=1,code='US.DEMO',origin=origin,horizon='1d',as_of_ms=end+2,issued_at_ms=end+3,
        stock_id=123,status='available',reference=reference,basis_evidence=basis,
        instrument={'instrument_class':'stock','signed_leverage':1},model=quantiles,baseline=copy.deepcopy(quantiles),
        window=dict(horizon='1d',sessions=[target],start=target,end=target,
            first_open_ms=calendar.open_ms(target),last_close_ms=calendar.close_ms(target),started=False))
    forecast['forecast_id']=q.sha(q.canonical(forecast))
    forecast_ref=f.put('predictions.json',dict(forecasts=[forecast]))
    cal=dict(name='XNYS',start='2026-01-01',end='2026-12-31',version=calendar.version)
    actuals=None;review_refs=[]
    if actual:
        known=calendar.close_ms(target)+1000
        bar={k:None for k in HISTORY_COLUMNS};bar.update(code='US.DEMO',session_date=target,
            open=100.,low=98.,high=103.,close=101.,volume=10.,turnover=1000.,currency='USD',
            adjustment='forward-excluding-dividends',source='fiction',source_at_ms=calendar.close_ms(target),
            retrieved_at_ms=known,known_at_ms=known,price_known_at_ms=known,currency_known_at_ms=known,
            completed=True,revision_vintage='fiction-v1')
        history=f.put('history.csv',csv_bytes([bar]));receipt=f.put('receipt.json',dict(identity_bindings=[
            dict(code='US.DEMO',stock_id=123,known_at_ms=end)]));evidence=f.put('basis.json',{'US.DEMO':basis})
        review=f.put('actual-review.json',dict(kind='reviewed-ohlc-actuals',decision='accepted',
            known_at='2026-10-21T01:00:00Z',forecasts_sha256=forecast_ref['sha256'],
            inputs_sha256=dict(history_csv=history['sha256'],receipt=receipt['sha256'],basis_evidence=evidence['sha256']),
            calendar=cal,targets=['low_return','high_return','terminal_logreturn']))
        actuals=dict(history_csv=history,receipt=receipt,basis_evidence=evidence,review=review);review_refs=[review]
    cohort=dict(cohort_id='saved',kind='saved_ohlc',forecasts=forecast_ref,actuals=actuals,
                calendar=cal,baseline='embedded-original-only')
    a=dict(schema_version=1,review_at='2026-10-21T06:00:00Z',qualification_policy=None,cohorts=[cohort])
    ref=f.put('analysis.json',a);domain=financial(a,ref['sha256'],cohort,review_refs)
    return f,a,ref,domain,forecast


def test_saved_ohlc_delegates_actual_metrics(calendar):
    f,a,r,d,_=ohlc_fixture(calendar)
    row=score(f,a,r,d)['rows'][0]
    assert row['scoring_status']=='scored' and row['baseline_available']
    assert row['low_endpoint_error']==pytest.approx(0)
    assert row['high_endpoint_error']==pytest.approx(1)
    assert row['model_metrics']['low_return']['coverage'] is True
    assert len(row['model_metrics']['terminal_logreturn']['pinball'])==3
    assert row['terminal_range_hit'] is None and row['point_absolute_error'] is None
    assert row['quality_status']=='insufficient'


def test_saved_pending_and_missing_actuals(calendar):
    f,a,r,d,_=ohlc_fixture(calendar,actual=False)
    a['review_at']='2026-10-20T18:00:00Z'
    row=score(f,a,r,d)['rows'][0]
    assert row['scoring_status']=='pending' and row['quality_status']=='pending'
    a['review_at']='2026-10-21T06:00:00Z'
    row=score(f,a,r,d)['rows'][0]
    assert row['scoring_status']=='missing_actual' and row['model_metrics'] is None


def test_calendar_span_is_bounded_before_library_allocation(calendar):
    f,a,r,d,_=ohlc_fixture(calendar,actual=False)
    a['cohorts'][0]['calendar'].update(start='1000-01-01',end='9999-01-01')
    with pytest.raises(ValueError,match='calendar-span-budget'):score(f,a,r,d)


def test_saved_forecast_hash_and_actual_source_identity(calendar):
    f,a,r,d,forecast=ohlc_fixture(calendar)
    forecast['model']['predicted_low']=99
    a['cohorts'][0]['forecasts']=f.replace(a['cohorts'][0]['forecasts'],dict(forecasts=[forecast]))
    d['cohorts'][0]['forecasts_sha256']=a['cohorts'][0]['forecasts']['sha256']
    with pytest.raises(ValueError,match='actual-ohlc-review'):score(f,a,r,d)


def test_saved_frozen_hash_rejects_even_when_actuals_absent(calendar):
    f,a,r,d,forecast=ohlc_fixture(calendar,actual=False)
    forecast['model']['predicted_low']=1
    c=a['cohorts'][0];c['forecasts']=f.replace(c['forecasts'],dict(forecasts=[forecast]))
    d['cohorts'][0]['forecasts_sha256']=c['forecasts']['sha256']
    row=score(f,a,r,d)['rows'][0]
    assert row['quality_status']=='failed' and 'immutable-forecast-id' in row['reasons'][0]


def test_saved_original_unavailable_is_withheld_not_missing_actual(calendar):
    f,a,r,d,forecast=ohlc_fixture(calendar,actual=False)
    forecast['status']='unavailable';forecast.pop('forecast_id');forecast['forecast_id']=q.sha(q.canonical(forecast))
    c=a['cohorts'][0];c['forecasts']=f.replace(c['forecasts'],dict(forecasts=[forecast]))
    d['cohorts'][0]['forecasts_sha256']=c['forecasts']['sha256']
    row=score(f,a,r,d)['rows'][0]
    assert row['scoring_status']=='withheld' and row['reasons']==['original-forecast-unavailable']


def test_saved_whole_window_cannot_be_issued_after_first_open(calendar):
    f,a,r,d,forecast=ohlc_fixture(calendar,actual=False)
    forecast['issued_at_ms']=forecast['window']['first_open_ms']+1
    forecast.pop('forecast_id');forecast['forecast_id']=q.sha(q.canonical(forecast))
    c=a['cohorts'][0];c['forecasts']=f.replace(c['forecasts'],dict(forecasts=[forecast]))
    d['cohorts'][0]['forecasts_sha256']=c['forecasts']['sha256']
    row=score(f,a,r,d)['rows'][0]
    assert row['scoring_status']=='invalid' and row['reasons']==['saved-full-window-issuance-after-start']


@pytest.mark.parametrize('case',['currency','identity','future','session','basis'])
def test_saved_actual_rejections_and_missing_availability(calendar,case):
    f,a,r,d,_=ohlc_fixture(calendar);c=a['cohorts'][0];actuals=c['actuals']
    if case in ('currency','future','session'):
        rows,_=q.csv_rows(f.files[actuals['history_csv']['path']]);bar=rows[0]
        if case=='currency':bar['currency']='MYR'
        elif case=='session':bar['session_date']='2026-10-19'
        else:
            for k in ('retrieved_at_ms','known_at_ms','price_known_at_ms','currency_known_at_ms'):
                bar[k]=str(q.milliseconds('2026-10-22T01:00:00Z'))
        actuals['history_csv']=f.replace(actuals['history_csv'],csv_bytes(rows))
    elif case=='identity':
        receipt=json.loads(f.files[actuals['receipt']['path']]);receipt['identity_bindings'][0]['stock_id']=999
        actuals['receipt']=f.replace(actuals['receipt'],receipt)
    else:
        basis=json.loads(f.files[actuals['basis_evidence']['path']]);basis['US.DEMO']['adjustment_vintage_id']='other'
        actuals['basis_evidence']=f.replace(actuals['basis_evidence'],basis)
    review=json.loads(f.files[actuals['review']['path']]);review['inputs_sha256']={
        k:actuals[k]['sha256'] for k in ('history_csv','receipt','basis_evidence')}
    actuals['review']=f.replace(actuals['review'],review)
    d['cohorts'][0]['accepted_outcome_review_sha256']=[actuals['review']['sha256']]
    row=score(f,a,r,d)['rows'][0]
    assert row['scoring_status']!='scored' and row['model_metrics'] is None
    assert row['quality_status'] in ('failed','insufficient')


def materialize(tmp_path):
    f,a,_,d,_,_=terminal_fixture()
    tmp_path.chmod(0o700)
    def real_ref(ref):
        path=tmp_path/Path(ref['path']).name
        path.write_bytes(f.files[ref['path']]);path.chmod(0o600)
        return dict(ref,path=str(path))
    c=a['cohorts'][0]
    for k in ('forecasts','original_batch','outcome_acceptance'):c[k]=real_ref(c[k])
    c['outcome_reviews']=[real_ref(x) for x in c['outcome_reviews']]
    path=tmp_path/'analysis.json';path.write_bytes(q.canonical(a));path.chmod(0o600)
    ar=dict(path=str(path),sha256=q.sha(path.read_bytes()),bytes=path.stat().st_size)
    d['analysis_sha256']=ar['sha256'];path=tmp_path/'financial.json';path.write_bytes(q.canonical(d));path.chmod(0o600)
    fr=dict(path=str(path),sha256=q.sha(path.read_bytes()),bytes=path.stat().st_size)
    bundle=dict(schema_version=1,kind='quality-scorecard-inputs',analysis=ar,financial_review=fr)
    path=tmp_path/'bundle.json';path.write_bytes(q.canonical(bundle));path.chmod(0o600)
    return path,q.sha(path.read_bytes())


def test_private_exclusive_reproducible_output(tmp_path):
    bundle,digest=materialize(tmp_path)
    before={p:p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    parents=[tmp_path/'first',tmp_path/'second']
    for p in parents:p.mkdir(mode=0o700)
    first=q.run(str(bundle),digest,str(parents[0]));second=q.run(str(bundle),digest,str(parents[1]))
    assert first['artifacts']==second['artifacts']
    assert before=={p:p.read_bytes() for p in before}
    for p in Path(first['folder']).iterdir():assert p.stat().st_mode & 0o777==0o600
    with pytest.raises(FileExistsError):q.run(str(bundle),digest,str(parents[0]))


def test_private_symlink_and_permissions_rejected(tmp_path):
    bundle,digest=materialize(tmp_path)
    bundle.chmod(0o644)
    with pytest.raises(ValueError,match='private-permissions'):q.run(str(bundle),digest,str(tmp_path))
    bundle.chmod(0o600);link=tmp_path/'link.json';link.symlink_to(bundle)
    with pytest.raises(ValueError,match='symlink'):q.private_read(link)


def test_cli_clean_directory_and_no_transport(tmp_path, monkeypatch):
    import subprocess
    import socket
    monkeypatch.setattr(socket,'create_connection',lambda *a,**kw:pytest.fail('network forbidden'))
    bundle,digest=materialize(tmp_path);output=tmp_path/'reports';output.mkdir(mode=0o700)
    result=subprocess.run([sys.executable,'-I','-B',str(SCRIPT/'quality_scorecard.py'),
        '--bundle',str(bundle),'--bundle-sha256',digest,'--output-parent',str(output)],
        cwd=tmp_path,capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)['status']=='scorecard-written'
