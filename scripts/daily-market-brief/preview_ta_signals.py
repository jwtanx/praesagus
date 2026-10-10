"""Render a local synthetic TA demonstration; never reads provider or account data."""
import argparse
import html
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def render_preview(assessment):
    """Render escaped assessment details without JavaScript or remote assets."""
    if not isinstance(assessment, dict) or assessment.get('synthetic') is not True:
        raise ValueError('Only synthetic assessments can be previewed')
    indicators = assessment.get('indicators')
    counts = assessment.get('counts')
    if not isinstance(indicators, list) or not isinstance(counts, dict):
        raise ValueError('Invalid assessment shape')
    statuses = {'bullish_event': 'Bullish event', 'bearish_event': 'Bearish event',
                'neutral': 'Neutral', 'unavailable': 'Unavailable'}
    names = [item.get('name') for item in indicators if isinstance(item, dict)]
    if len(indicators) != 3 or set(names) != {'KDJ', 'MACD', 'BOLL'}:
        raise ValueError('Three distinct indicators required')
    expected = {'bullish': 0, 'bearish': 0, 'neutral': 0, 'unavailable': 0}
    for item in indicators:
        if item.get('status') not in statuses:
            raise ValueError('Invalid indicator status')
        key = {'bullish_event': 'bullish', 'bearish_event': 'bearish'}.get(item['status'], item['status'])
        expected[key] += 1
    expected.update(expected=3, evaluated=3-expected['unavailable'])
    if any(type(counts.get(key)) is not int or counts[key] != value for key, value in expected.items()):
        raise ValueError('Count/status mismatch')
    esc = lambda value: html.escape(str(value), quote=True)
    cards = []
    for item in indicators:
        details = {key: item.get(key) for key in ('rule', 'rule_version', 'parameters', 'prior_session',
                    'current_session', 'prior_close_at', 'current_close_at', 'prior_times', 'current_times',
                    'prior_values', 'current_values', 'reasons')}
        json.dumps(details, allow_nan=False)  # Reject nonfinite values before rendering.
        def display(value):
            if value is None: return 'Unavailable'
            if isinstance(value, dict): return ', '.join(f'{key}: {item}' for key, item in value.items())
            if isinstance(value, list): return '; '.join(str(item) for item in value) or 'None'
            return str(value)
        labels = {'rule': 'Event rule', 'rule_version': 'Method version', 'parameters': 'Parameters',
                  'prior_session': 'Prior session', 'current_session': 'Current session',
                  'prior_close_at': 'Prior session close', 'current_close_at': 'Current session close',
                  'prior_times': 'Prior evidence times', 'current_times': 'Current evidence times',
                  'prior_values': 'Prior values', 'current_values': 'Current values', 'reasons': 'Missing-data reasons'}
        details_text = '<dl>' + ''.join(f'<dt>{labels[key]}</dt><dd>{esc(display(value))}</dd>'
                                      for key, value in details.items()) + '</dl>'
        cards.append(f'<details><summary><strong>{esc(item["name"])}</strong> · '
                     f'{esc(statuses[item["status"]])}</summary>{details_text}</details>')
    return f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PRSG-82 · Synthetic technical-event preview</title>
<style>body{{font:16px/1.5 system-ui;background:#101822;color:#edf2f7;max-width:760px;margin:40px auto;padding:20px}}
h1{{font-size:1.8rem}}.notice{{background:#453618;padding:16px;border:1px solid #d6af58;border-radius:10px}}
.counts{{font-size:1.2rem;padding:20px 0}}details{{border:1px solid #59697b;border-radius:8px;margin:12px 0;padding:14px}}
summary{{cursor:pointer}}summary:focus-visible{{outline:3px solid #a3c9ff}}dt{{font-weight:650;margin-top:12px}}dd{{margin:3px 0;overflow-wrap:anywhere;font-size:.9rem}}
.muted{{color:#b8c7d8}}</style>
<main><p class="notice"><strong>Synthetic simulation.</strong> These authored values are not live Moomoo signals.
No provider connection, entitlement, coverage or predictive performance is established.</p>
<h1>{esc(assessment.get('ticker', 'Unknown ticker'))} · Technical events</h1>
<p>Praesagus rules applied to simulated provider-calculated values. Counts are observations, not probabilities or independent votes.</p>
<p class="counts">Bullish {counts['bullish']} · Bearish {counts['bearish']} · Neutral {counts['neutral']} · Unavailable {counts['unavailable']}</p>
<p class="muted">Evaluated {counts['evaluated']} / 3 · Expected completed session: {esc(assessment.get('expected_session'))}<br>
Cutoff: {esc(assessment.get('cutoff'))}</p>
<p>Open an indicator for its rule, parameters, session dates, values and missing-data reasons.</p>
{''.join(cards)}
<p class="muted">Events expire when the next session completes. Bollinger re-entry is a chosen mean-reversion display convention.
Forecast direction, targets and confidence remain separate.</p></main></html>'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--scenario', choices=('complete', 'partial', 'unavailable'), default='complete')
    args = parser.parse_args(argv)
    try:
        from ingest.ta_signal_assessment import assess_ticker, synthetic_demo
        case = synthetic_demo()
        if args.scenario == 'partial':
            case['record']['indicators'].pop('MACD', None)
        elif args.scenario == 'unavailable':
            case['record']['indicators'] = {}
        assessment = assess_ticker(case['record'], calendar=case['calendar'], cutoff=case['cutoff'])
        content = render_preview(assessment)
        destination = Path(args.output)
        if not destination.is_absolute() or destination != destination.resolve() or destination.is_relative_to(REPO):
            raise ValueError('Preview must be outside the repository')
        if destination.suffix != '.html':
            raise ValueError('HTML output required')
        with destination.open('x', encoding='utf-8') as stream:
            stream.write(content)
    except (ValueError, OSError, TypeError, KeyError):
        print('Synthetic preview failed; no existing output overwritten.', file=sys.stderr)
        return 1
    print('Synthetic preview written.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
