"""Build a low-confidence drift/volatility baseline from completed daily closes.

This is a transparent statistical reference range, not a validated alpha model.
"""
from datetime import date, datetime, time, timezone
import math
import statistics
from zoneinfo import ZoneInfo


MODEL = '20-session log-return drift with a 95% Gaussian volatility band'
SESSION_CLOSE = {'US': time(16, 0), 'MY': time(17, 0)}


def build_baseline(
    bars,
    *,
    market,
    currency,
    as_of,
    target_date,
    horizon_sessions,
    reference_source,
):
    """Return a forecast row fragment from Yahoo-style daily bars.

    Each bar has timestamp (Unix seconds at the exchange session open),
    close, adjusted_close and timezone. The session close is reconstructed
    from the exchange-local bar date, then compared with the frozen cutoff so
    an incomplete daily candle cannot enter the model.
    """
    if market not in SESSION_CLOSE or currency != {'US': 'USD', 'MY': 'MYR'}[market]:
        raise ValueError('market/currency pair is unsupported or inconsistent')
    if type(horizon_sessions) is not int or horizon_sessions < 1:
        raise ValueError('horizon_sessions must be a positive integer')
    if not isinstance(reference_source, str) or not reference_source.startswith('https://'):
        raise ValueError('reference_source must be HTTPS')
    cutoff = datetime.fromisoformat(as_of.replace('Z', '+00:00'))
    if cutoff.tzinfo is None:
        raise ValueError('as_of must include a timezone')
    target = date.fromisoformat(target_date)
    eligible = []
    for bar in bars:
        try:
            tz = ZoneInfo(bar['timezone'])
            opened = datetime.fromtimestamp(bar['timestamp'], timezone.utc).astimezone(tz)
            close_at = datetime.combine(opened.date(), SESSION_CLOSE[market], tzinfo=tz)
            close = float(bar['close'])
            adjusted = float(bar['adjusted_close'])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if close_at <= cutoff.astimezone(tz) and close > 0 and adjusted > 0:
            eligible.append((opened.date(), close, adjusted))
    eligible.sort(key=lambda x: x[0])
    # Require 20 returns, which means 21 completed closing observations.
    eligible = eligible[-21:]
    if len(eligible) < 21:
        raise ValueError('at least 21 completed daily closes are required')
    returns = [math.log(eligible[i][2] / eligible[i - 1][2]) for i in range(1, len(eligible))]
    if not all(math.isfinite(x) for x in returns):
        raise ValueError('return history contains a non-finite value')
    drift = statistics.mean(returns)
    volatility = statistics.stdev(returns)
    if volatility <= 0:
        raise ValueError('return history has no measurable volatility')
    reference_date, reference_close, _ = eligible[-1]
    expected_log_return = drift * horizon_sessions
    mid = reference_close * math.exp(expected_log_return)
    band = 1.96 * volatility * math.sqrt(horizon_sessions)
    low = mid * math.exp(-band)
    high = mid * math.exp(band)
    if not all(math.isfinite(x) and x > 0 for x in (mid, low, high)):
        raise ValueError('model produced an invalid price range')
    # Require drift to be at least one quarter of the modeled horizon move
    # before assigning a direction; otherwise the baseline is sideways.
    threshold = 0.25 * volatility * math.sqrt(horizon_sessions)
    direction = 'up' if expected_log_return > threshold else 'down' if expected_log_return < -threshold else 'flat'
    precision = 2
    rounded_mid, rounded_low, rounded_high = (round(x, precision) for x in (mid, low, high))
    symbol = 'US$' if currency == 'USD' else 'MYR '
    label = {'up': 'Bullish', 'down': 'Bearish', 'flat': 'Sideways'}[direction]
    reference_close = round(reference_close, precision)
    return {
        'current_price': f'{symbol}{reference_close:.{precision}f}',
        'current_price_value': reference_close,
        'price_as_of': reference_date.isoformat() + ' completed close',
        'quote_status': 'observed',
        'reference_close_date': reference_date.isoformat(),
        'reference_close': reference_close,
        'direction': direction,
        'direction_label': label,
        'estimated_mid_case_value': rounded_mid,
        'estimated_mid_case': f'{symbol}{rounded_mid:.{precision}f}',
        'range_low_value': rounded_low,
        'range_high_value': rounded_high,
        'estimated_range': f'{symbol}{rounded_low:.{precision}f}–{rounded_high:.{precision}f}',
        'forecast_status': 'rated',
        'confidence': 'low',
        'confidence_reason': (
            'Low-confidence statistical baseline from 20 completed daily adjusted-close returns; '
            'Gaussian range assumption, no out-of-sample calibration or event adjustment.'
        ),
        'forecast_model': MODEL,
        'forecast_observations': 20,
        'forecast_horizon_sessions': horizon_sessions,
        'forecast_basis': {
            'reference_close_date': reference_date.isoformat(),
            'reference_close': reference_close,
            'reference_source': reference_source,
            'horizon_type': 'week_end' if target.weekday() == 4 else 'next_session',
            'bull_case': f'If recent drift persists, upper model band is {symbol}{rounded_high:.{precision}f}.',
            'bear_case': f'If recent drift reverses, lower model band is {symbol}{rounded_low:.{precision}f}.',
            'invalidation': (
                f'Target close outside {symbol}{rounded_low:.{precision}f}–'
                f'{symbol}{rounded_high:.{precision}f} invalidates this statistical range.'
            ),
        },
        'forecast_source': reference_source,
        'forecast_reference_observations': 21,
    }
