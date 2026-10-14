"""Pure normal-report forecast overlay; no intake, admission or publication."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from ingest.forecast_scenario import (_bounded, _time, REASONS,
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

STALE_GAPS = frozenset({
    'Completed history and verified close/currency/adjustment reference unavailable.',
    'No supported numeric target/range method.',
    *REASONS.values(),
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
        if not _bounded(template) or type(template) is not dict or template_reviewed is not True:
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
