"""Pure normal-report forecast overlay; no intake, admission or publication."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from ingest.forecast_scenario import (_bounded, _time, _row_identity, _hash, REASONS,
                                     build_forecast_scenario, apply_scenario_to_row)

# Reuse the authoritative script's reference semantics; no second report grader.
_SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts/daily-market-brief'
_spec = importlib.util.spec_from_file_location('_report_forecast_validator', _SCRIPT_DIR / 'validate_report_json.py')
validator = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(_SCRIPT_DIR))
try:
    _spec.loader.exec_module(validator)
finally:
    sys.path.pop(0)

REPORT_TEMPLATE_MAX_DEPTH = 12
BATCH_MAX_BYTES = 2 * 1024 * 1024
BATCH_MAX_ITEMS = 50
BATCH_INPUT_GAPS = dict(
    batch_entry_missing='Per-instrument evidence/admission batch entry is missing.',
    evidence_missing='Per-instrument forecast evidence is missing.',
    admission_missing=REASONS['admission_missing'],
)

STALE_GAPS = frozenset({
    'Completed history and verified close/currency/adjustment reference unavailable.',
    'No supported numeric target/range method.',
    *REASONS.values(),
    *BATCH_INPUT_GAPS.values(),
})


class ReportForecastError(ValueError):
    def __init__(self):
        super().__init__('report-forecast-invalid-input')


def prepare_report_forecast(template, *, evidence, admission, issued_at,
                            report_cutoff, template_reviewed):
    """Copy one matching row and refresh reference coverage; caller reviews prose.

    template_reviewed is only a workflow attestation. It authenticates neither
    narrative, sources, complete events, licensing nor reviewer declarations.
    Full public/compact/universe/calendar validation is the CLI's I/O step.
    """
    try:
        if not _bounded(template,max_depth=REPORT_TEMPLATE_MAX_DEPTH) or type(template) is not dict or template_reviewed is not True:
            raise ReportForecastError()
        meta = template['metadata']
        if (template['schema_version'] != 3 or type(template['schema_version']) is not int
                or meta['presentation_profile'] != 'compact-v1'
                or meta['as_of'] != report_cutoff or _time(issued_at) > _time(report_cutoff)
                or meta['date'] != _time(report_cutoff).astimezone(ZoneInfo('Asia/Kuala_Lumpur')).date().isoformat()):
            raise ReportForecastError()
        rows = template['forecasts']
        if type(rows) is not list or any(type(r) is not dict for r in rows):
            raise ReportForecastError()
        indices = [n for n, r in enumerate(rows) if r.get('ticker') == 'SPY' and r.get('market') == 'US']
        if len(indices) != 1 or rows[indices[0]].get('currency') != 'USD':
            raise ReportForecastError()
        if type(template['collection']) is not dict:
            raise ReportForecastError()
        result = build_forecast_scenario(evidence, admission=admission if evidence is not None else None,
                                         issued_at=issued_at, report_cutoff=report_cutoff)
        target = rows[indices[0]]
        if result['status'] == 'generated' and any(gap in STALE_GAPS for gap in target['data_gaps']):
            raise ReportForecastError()
        report = deepcopy(template)
        report['forecasts'][indices[0]] = apply_scenario_to_row(target, result)
        report['collection']['verified_forecast_reference_count'] = sum(
            validator.compact_reference(row.get('forecast_basis'), _time(report_cutoff))
            for row in report['forecasts'])
        audit = dict(schema_version=1, status=result['status'], reasons=deepcopy(result['reasons']),
                     issued_at=issued_at, report_cutoff=report_cutoff,
                     private_audit=deepcopy(result['private_audit']))
        return dict(status=result['status'], reasons=deepcopy(result['reasons']), report=report, audit=audit)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ReportForecastError() from None


def prepare_report_forecasts(template, *, batch, issued_at, report_cutoff, template_reviewed):
    """Pure bounded per-row preparation; missing entries withhold, never reuse numbers.

    Batch schema1: exact {schema_version, items}; each item has exactly
    {ticker, market, currency, evidence, admission}. Identity/binding failures are
    fatal before mapping. Core evidence gates remain per-row withholding reasons.
    All template rows are intended targets, including those absent from items.
    input_reasons distinguish missing pairs from the unchanged core result reasons.
    Public validation and immutable private writes remain the caller's I/O boundary.
    """
    try:
        if (template_reviewed is not True or not _bounded(template,max_depth=REPORT_TEMPLATE_MAX_DEPTH)
                or type(template) is not dict or not _bounded(batch,max_depth=12)
                or type(batch) is not dict or set(batch)!={'schema_version','items'}
                or type(batch['schema_version']) is not int or batch['schema_version']!=1
                or type(batch['items']) is not list or len(batch['items'])>BATCH_MAX_ITEMS
                or len(json.dumps(batch,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8'))>BATCH_MAX_BYTES):
            raise ReportForecastError()
        meta=template['metadata']
        if (type(template['schema_version']) is not int or template['schema_version']!=3
                or meta['presentation_profile']!='compact-v1' or meta['as_of']!=report_cutoff
                or _time(issued_at)>_time(report_cutoff)
                or meta['date']!=_time(report_cutoff).astimezone(ZoneInfo('Asia/Kuala_Lumpur')).date().isoformat()
                or type(template['collection']) is not dict):
            raise ReportForecastError()
        rows=template['forecasts']
        if type(rows) is not list or not 0<len(rows)<=BATCH_MAX_ITEMS:
            raise ReportForecastError()
        intended={}
        for row in rows:
            if type(row) is not dict:
                raise ReportForecastError()
            identity={k:row.get(k) for k in ('ticker','market','currency')}
            if not _row_identity(identity):
                raise ReportForecastError()
            key=(identity['ticker'],identity['market'])
            if key in intended:
                raise ReportForecastError()
            intended[key]=identity
        supplied={}
        for item in batch['items']:
            if type(item) is not dict or set(item)!={'ticker','market','currency','evidence','admission'}:
                raise ReportForecastError()
            identity={k:item[k] for k in ('ticker','market','currency')}
            if not _row_identity(identity):
                raise ReportForecastError()
            key=(identity['ticker'],identity['market'])
            if key in supplied or intended.get(key)!=identity:
                raise ReportForecastError()
            evidence,admission=item['evidence'],item['admission']
            if evidence is not None:
                if (type(evidence) is not dict or type(evidence.get('instrument')) is not dict
                        or any(evidence['instrument'].get(k)!=v for k,v in identity.items())):
                    raise ReportForecastError()
                # Batch uses generic evidence; singleton schema1/2 remains legacy-only.
                if type(evidence.get('schema_version')) is not int or evidence['schema_version']!=3:
                    raise ReportForecastError()
            if admission is not None:
                if type(admission) is not dict:
                    raise ReportForecastError()
                if evidence is not None and 'evidence_sha256' in admission and admission['evidence_sha256']!=_hash(evidence):
                    raise ReportForecastError()
            supplied[key]=item
        report=deepcopy(template)
        audits=[];all_reasons=set();generated=missing=0
        for index,target in enumerate(rows):
            key=(target['ticker'],target['market']);identity=intended[key]
            item=supplied.get(key)
            input_reasons=[]
            if item is None:
                missing+=1;input_reasons=['batch_entry_missing']
                evidence=admission=None
            else:
                evidence,admission=item['evidence'],item['admission']
                if evidence is None:input_reasons.append('evidence_missing')
                if admission is None:input_reasons.append('admission_missing')
            result=build_forecast_scenario(evidence,admission=admission if evidence is not None else None,
                issued_at=issued_at,report_cutoff=report_cutoff)
            if result['status']=='generated' and any(gap in STALE_GAPS for gap in target['data_gaps']):
                raise ReportForecastError()
            mapped=apply_scenario_to_row(target,result,identity=identity)
            for reason in input_reasons:
                if BATCH_INPUT_GAPS[reason] not in mapped['data_gaps']:
                    mapped['data_gaps'].append(BATCH_INPUT_GAPS[reason])
            report['forecasts'][index]=mapped
            generated+=int(result['status']=='generated')
            reasons=sorted(set(result['reasons'])|set(input_reasons));all_reasons.update(reasons)
            audits.append(dict(identity,status=result['status'],reasons=reasons,input_reasons=input_reasons,
                core_reasons=deepcopy(result['reasons']),private_audit=deepcopy(result['private_audit'])))
        report['collection']['verified_forecast_reference_count']=sum(
            validator.compact_reference(row.get('forecast_basis'),_time(report_cutoff)) for row in report['forecasts'])
        counts=dict(intended=len(rows),provided=len(supplied),generated=generated,withheld=len(rows)-generated,missing_entries=missing)
        counts.update(missing_pairs=sum(bool(a['input_reasons']) for a in audits),
            missing_evidence=sum(any(r in a['input_reasons'] for r in ('batch_entry_missing','evidence_missing')) for a in audits),
            missing_admission=sum(any(r in a['input_reasons'] for r in ('batch_entry_missing','admission_missing')) for a in audits))
        status='generated' if generated==len(rows) else 'partial' if generated else 'withheld'
        audit=dict(schema_version=2,status=status,issued_at=issued_at,report_cutoff=report_cutoff,counts=counts,rows=audits)
        return dict(status=status,reasons=sorted(all_reasons),report=report,audit=audit,counts=counts)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
        raise ReportForecastError() from None
