import { FormEvent, useState } from 'react';
import { fetchMoomooHistory, MoomooHistoryPoint, MoomooHistoryResponse } from '../services/api';

function validSeries(value: MoomooHistoryResponse): MoomooHistoryPoint[] | null {
  if (!value || !Array.isArray(value.series) || value.series.length > 100
    || !/^\d{4}-\d{2}-\d{2}$/.test(value.start) || !/^\d{4}-\d{2}-\d{2}$/.test(value.end)
    || !Number.isFinite(Date.parse(value.retrieved_at))) return null;
  let previous = '';
  const points: MoomooHistoryPoint[] = [];
  for (const point of value.series) {
    if (!point || typeof point.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(point.date)) return null;
    const time = Date.parse(`${point.date}T00:00:00Z`);
    if (!Number.isFinite(time) || new Date(time).toISOString().slice(0, 10) !== point.date
      || point.date < value.start || point.date > value.end || point.date <= previous
      || typeof point.close !== 'number' || !Number.isFinite(point.close) || point.close <= 0) return null;
    previous = point.date;
    points.push(point);
  }
  return points;
}

function chartPoints(series: MoomooHistoryPoint[]) {
  const values = series.map(point => point.close);
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || Math.max(max * 0.02, 1);
  return series.map((point, index) => ({
    ...point,
    x: series.length === 1 ? 50 : 8 + index * 84 / (series.length - 1),
    y: max === min ? 50 : 92 - ((point.close - min) / span) * 84,
  }));
}

export default function MoomooPriceTrend() {
  const [code, setCode] = useState('US.AAPL');
  const [window, setWindow] = useState<'1M' | '3M'>('1M');
  const [result, setResult] = useState<MoomooHistoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load(event: FormEvent) {
    event.preventDefault();
    const normalized = code.trim().toUpperCase();
    if (normalized.length > 14 || !/^US\.[A-Z0-9]+(?:[.-][A-Z0-9]+)*$/.test(normalized)) {
      setError('Enter a valid US symbol, for example US.AAPL.');
      setResult(null);
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetchMoomooHistory(normalized, window);
      const series = validSeries(response);
      if (response.code !== normalized || response.window !== window || response.adjustment !== 'QFQ'
        || !Number.isInteger(response.count) || response.count !== response.series.length || !series) {
        throw new Error('Moomoo returned invalid historical data.');
      }
      setResult(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Historical data request failed.';
      setError(message.includes('503') ? 'OpenD is unavailable. Check that it is running and logged in, then retry.'
        : message.includes('502') ? 'OpenD could not return this history. Check US market-data entitlement, then retry.'
          : message);
    } finally {
      setLoading(false);
    }
  }

  const points = result?.series.length ? chartPoints(result.series) : [];

  return (
    <section className="chart-card moomoo-history-card" aria-labelledby="moomoo-history-title">
      <h3 id="moomoo-history-title">Moomoo historical price trend</h3>
      <p>Historical daily close · adjusted (QFQ). Provider observations, not a forecast; the latest bar may still reflect an active session.</p>
      <form onSubmit={load}>
        <label htmlFor="moomoo-history-code">US symbol</label>{' '}
        <input id="moomoo-history-code" value={code} maxLength={14} onChange={event => setCode(event.target.value)} />{' '}
        <label htmlFor="moomoo-history-window">Range</label>{' '}
        <select id="moomoo-history-window" value={window} onChange={event => setWindow(event.target.value as '1M' | '3M')}>
          <option value="1M">1 month</option><option value="3M">3 months</option>
        </select>{' '}
        <button type="submit" disabled={loading}>{loading ? 'Loading history…' : 'Load price trend'}</button>
      </form>
      {loading && <p role="status">Requesting historical daily closes from Moomoo OpenD…</p>}
      {error && <p role="alert">{error}</p>}
      {result && points.length === 0 && <p role="status">No historical daily closes returned for {result.code} in this range.</p>}
      {result && points.length > 0 && <>
        <p>{result.code} · {result.window} · {points[0].date} to {points[points.length - 1].date} · Retrieved {result.retrieved_at} UTC</p>
        <svg viewBox="0 0 100 100" role="img" aria-label={`${result.code} adjusted daily closing prices from ${points[0].date} to ${points[points.length - 1].date}`} preserveAspectRatio="none" style={{ width: '100%', height: 220 }}>
          <polyline points={points.map(point => `${point.x},${point.y}`).join(' ')} fill="none" stroke="currentColor" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
          {points.map(point => <circle key={point.date} cx={point.x} cy={point.y} r="1.2" fill="currentColor"><title>{point.date}: {point.close}</title></circle>)}
        </svg>
        <p>Session dates are exchange-local dates. Close currency is not inferred.</p>
      </>}
    </section>
  );
}
