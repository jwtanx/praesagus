from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
import sys

import pytest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'scripts/daily-market-brief'))
from statistical_baseline import build_baseline


def bars_for(market, end_date, count=22):
    zone_name = 'America/New_York' if market == 'US' else 'Asia/Kuala_Lumpur'
    zone = ZoneInfo(zone_name)
    rows = []
    day = date.fromisoformat(end_date)
    while len(rows) < count:
        if day.weekday() < 5:
            open_time = time(9, 30) if market == 'US' else time(9, 0)
            stamp = datetime.combine(day, open_time, tzinfo=zone).timestamp()
            close = 100 + len(rows) * 0.05 + (len(rows) % 3) * 0.2
            rows.append({'timestamp': stamp, 'close': close, 'adjusted_close': close, 'timezone': zone_name})
        day -= timedelta(days=1)
    return list(reversed(rows))


def test_us_incomplete_report_day_does_not_enter_reference_close():
    bars = bars_for('US', '2026-10-07')
    result = build_baseline(
        bars, market='US', currency='USD', as_of='2026-10-07T10:35:00-04:00',
        target_date='2026-10-09', horizon_sessions=3,
        reference_source='https://finance.yahoo.com/quote/QQQ/history/',
    )
    assert result['reference_close_date'] == '2026-10-06'
    assert result['forecast_horizon_sessions'] == 3
    assert result['forecast_status'] == 'rated'
    assert result['range_low_value'] < result['estimated_mid_case_value'] < result['range_high_value']
    assert result['confidence'] == 'low'


def test_malaysia_completed_report_day_can_be_used():
    bars = bars_for('MY', '2026-10-07')
    result = build_baseline(
        bars, market='MY', currency='MYR', as_of='2026-10-07T22:35:00+08:00',
        target_date='2026-10-09', horizon_sessions=2,
        reference_source='https://finance.yahoo.com/quote/1155.KL/history/',
    )
    assert result['reference_close_date'] == '2026-10-07'
    assert result['forecast_basis']['horizon_type'] == 'week_end'


def test_rejects_inconsistent_currency_and_short_history():
    with pytest.raises(ValueError, match='market/currency'):
        build_baseline([], market='MY', currency='USD', as_of='2026-10-07T22:35:00+08:00',
                       target_date='2026-10-09', horizon_sessions=2,
                       reference_source='https://finance.yahoo.com/quote/1155.KL/history/')
    with pytest.raises(ValueError, match='21 completed'):
        build_baseline(bars_for('US', '2026-10-07', count=20), market='US', currency='USD',
                       as_of='2026-10-07T10:35:00-04:00', target_date='2026-10-09',
                       horizon_sessions=3, reference_source='https://finance.yahoo.com/quote/QQQ/history/')
