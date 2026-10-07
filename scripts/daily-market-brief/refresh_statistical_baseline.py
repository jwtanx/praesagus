#!/usr/bin/env python3
"""Add a reproducible low-confidence 20-session baseline to a schema-3 report."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from statistical_baseline import build_baseline

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / 'artifacts' / 'daily-market-brief'


def fetch_history(ticker, market, as_of, target_date):
    symbol = ticker + ('.KL' if market == 'MY' else '')
    start = date.fromisoformat(as_of[:10]) - timedelta(days=50)
    end = date.fromisoformat(target_date) + timedelta(days=1)
    period1 = int(datetime.combine(start, datetime.min.time(), timezone.utc).timestamp())
    period2 = int(datetime.combine(end, datetime.min.time(), timezone.utc).timestamp())
    url = (
        f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}'
        f'?period1={period1}&period2={period2}&interval=1d&events=div%2Csplits'
    )
    request = Request(url, headers={'User-Agent': 'Praesagus daily report historical baseline/1.0'})
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    chart = payload.get('chart') or {}
    if chart.get('error') or not chart.get('result'):
        raise ValueError('historical price series unavailable')
    result = chart['result'][0]
    meta = result['meta']
    quotes = result['indicators']['quote'][0]
    adjusted = result['indicators'].get('adjclose', [{}])[0].get('adjclose') or []
    bars = [
        {
            'timestamp': timestamp,
            'close': close,
            'adjusted_close': adj_close,
            'timezone': meta['exchangeTimezoneName'],
        }
        for timestamp, close, adj_close in zip(result.get('timestamp', []), quotes.get('close', []), adjusted)
    ]
    return symbol, meta.get('currency'), bars


def horizon_sessions(market, as_of, target_date):
    # The daily report currently targets the same week. Holidays are visible
    # in the shared calendar and require operator override via target/horizon
    # if the target falls across a market closure.
    start = date.fromisoformat(as_of[:10])
    end = date.fromisoformat(target_date)
    count = sum(1 for offset in range((end - start).days + 1)
                if (start + timedelta(days=offset)).weekday() < 5)
    zone = ZoneInfo('America/New_York' if market == 'US' else 'Asia/Kuala_Lumpur')
    cutoff_local = datetime.fromisoformat(as_of.replace('Z', '+00:00')).astimezone(zone)
    close = datetime.strptime('16:00' if market == 'US' else '17:00', '%H:%M').time()
    # When the report is after today's cash close, its completed close is the
    # baseline and that date is excluded from the forward session count.
    if cutoff_local.time() >= close:
        count -= 1
    return max(1, count)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', required=True, help='Existing schema-3 report date')
    parser.add_argument('--target-date', help='Override each row target date')
    args = parser.parse_args()
    path = REPORTS / f'{args.date}.json'
    report = json.loads(path.read_text(encoding='utf-8'))
    if report.get('schema_version') != 3 or report.get('metadata', {}).get('date') != args.date:
        raise SystemExit('target must be an existing schema-3 report')
    as_of = report['metadata']['as_of']
    prepared = []
    failures = []
    for row in report['forecasts']:
        target = args.target_date or row.get('target_date')
        if not target:
            failures.append(f"{row['ticker']}: target date missing")
            continue
        try:
            symbol, provider_currency, bars = fetch_history(row['ticker'], row['market'], as_of, target)
            if provider_currency != row['currency']:
                raise ValueError('historical series currency does not match report listing currency')
            source_url = f'https://finance.yahoo.com/quote/{quote(symbol)}/history/'
            model = build_baseline(
                bars, market=row['market'], currency=row['currency'], as_of=as_of,
                target_date=target,
                horizon_sessions=horizon_sessions(row['market'], as_of, target),
                reference_source=source_url,
            )
            prepared.append((row, target, model, source_url, symbol))
        except Exception as exc:
            failures.append(f"{row['ticker']}: {exc}")
    if failures:
        raise SystemExit('No report changes written; baseline failed for:\n' + '\n'.join(failures))
    for row, target, model, source_url, symbol in prepared:
        row['forecast_as_of'] = as_of
        row['target_date'] = target
        row['forecast_status'] = model['forecast_status']
        row['direction'] = model['direction']
        row['direction_label'] = model['direction_label']
        row['estimated_mid_case'] = model['estimated_mid_case']
        row['estimated_mid_case_value'] = model['estimated_mid_case_value']
        row['estimated_range'] = model['estimated_range']
        row['range_low_value'] = model['range_low_value']
        row['range_high_value'] = model['range_high_value']
        row['confidence'] = model['confidence']
        row['confidence_reason'] = model['confidence_reason']
        row['forecast_model'] = model['forecast_model']
        row['forecast_observations'] = model['forecast_observations']
        row['forecast_horizon_sessions'] = model['forecast_horizon_sessions']
        row['forecast_basis'] = model['forecast_basis']
        row['scenario'] = 'Low-confidence statistical baseline; recent drift and volatility.'
        row['sources'] = [{
            'label': 'Historical daily prices · reference close and baseline inputs',
            'url': source_url,
            'provider_symbol': symbol,
            'reference_close_date': model['reference_close_date'],
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'price_observations': model['forecast_reference_observations'],
        }]
        if row.get('public_snapshot'):
            # Point snapshot and forecast reference are different price facts.
            # Keep the point unsortable and make the series units gap explicit.
            row['current_price'] = 'Point snapshot'
            row['current_price_value'] = None
            row['quote_status'] = 'missing'
            row['price_as_of'] = 'Report-time point snapshot; vendor units not used as forecast anchor'
            gaps = [g for g in row.get('data_gaps', [])
                    if g not in {'no_publishable_reference_close', 'unsupported_price_forecast'}]
            if 'point_snapshot_units_unverified' not in gaps:
                gaps.append('point_snapshot_units_unverified')
            row['data_gaps'] = gaps
        else:
            row['current_price'] = model['current_price']
            row['current_price_value'] = model['current_price_value']
            row['quote_status'] = model['quote_status']
            row['price_as_of'] = model['price_as_of']
            row['data_gaps'] = [g for g in row.get('data_gaps', [])
                                if g not in {'no_publishable_reference_close', 'unsupported_price_forecast'}]
    report['metadata']['disclaimer'] = (
        'Research only. Every row has a low-confidence short-horizon price range. '
        'Trend colors show the model direction; ranges are not trade instructions.'
    )
    report['summary'][0].update({
        'title': '50 baseline forecasts',
        'summary': 'All 50 names have a short-horizon price range. Trend colors show the estimated direction; confidence is low.',
    })
    report['sections']['top10']['description'] = [{
        'text': 'Every name has a low-confidence statistical range. Bullish, bearish, and sideways colors show model drift.',
        'sources': [],
    }]
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'{args.date}: wrote {len(prepared)} low-confidence forecast ranges')
    for row, _, model, _, _ in prepared:
        print(f"{row['market']}:{row['ticker']} {model['direction']} {model['estimated_range']}")


if __name__ == '__main__':
    main()
