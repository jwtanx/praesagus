import { useEffect, useRef, useState } from 'react';
import { CatalystRecord, CatalystResponse, fetchFinancialCatalysts } from '../services/api';
import './CatalystInbox.css';

export function catalystSourceUrl(value: string | null): string | null {
  if (!value || /[\s\\]/.test(value)) return null;
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

export function catalystWarnings(data: CatalystResponse): string[] {
  return Object.entries(data.dataset_status).flatMap(([dataset, state]) => {
    const label = dataset.replace(/_/g, ' ');
    if (state.status !== 'loaded') return [`${label}: ${state.status === 'absent' ? 'dataset absent' : 'dataset unreadable or malformed'}`];
    return state.rows_skipped ? [`${label}: ${state.rows_skipped} malformed rows skipped`] : [];
  });
}

export function catalystTime(record: CatalystRecord): string {
  if (!record.event_at) return 'Event time unavailable or ambiguous';
  if (record.time_precision === 'date') return `${record.event_at} · date only${record.timezone ? ` · ${record.timezone}` : ' · timezone unavailable'}`;
  return `${record.event_at} · UTC`;
}

function Evidence({ record }: { record: CatalystRecord }) {
  const url = catalystSourceUrl(record.source_url);
  return <article className="catalyst-record">
    <div className="catalyst-record-heading"><strong>{record.ticker || 'Global / ticker unavailable'}</strong><span>{record.event_type.replace(/_/g, ' ')}{record.subtype ? ` · ${record.subtype}` : ''}{record.estimated ? ' · estimated' : ''}</span></div>
    <h5>{record.title}</h5>
    <p>{catalystTime(record)}</p>
    <p>Source: {record.source || 'Provider unavailable'} · {url ? <a href={url} target="_blank" rel="noopener noreferrer">Open original source ↗</a> : 'Source link unavailable'}</p>
    <details><summary>Provenance and data gaps{record.data_gaps.length ? ` (${record.data_gaps.length})` : ''}</summary>
      <dl><dt>Source ID</dt><dd>{record.source_id || 'Unavailable; exact-record hash used'}</dd>
        <dt>Published / disclosed (original)</dt><dd>{record.published_at || 'Unavailable'}</dd>
        <dt>Available / first observed (original)</dt><dd>{record.available_at || 'Unavailable'}</dd>
        <dt>Ingested (original)</dt><dd>{record.ingested_at || 'Unavailable'}</dd>
        <dt>Original event time</dt><dd>{typeof record.raw_event_at === 'string' ? record.raw_event_at : JSON.stringify(record.raw_event_at) || 'Unavailable'}</dd></dl>
      {record.data_gaps.length > 0 && <ul>{record.data_gaps.map(gap => <li key={gap}>{gap}</li>)}</ul>}
    </details>
  </article>;
}

export default function CatalystInbox() {
  const [ticker, setTicker] = useState('');
  const [eventType, setEventType] = useState('');
  const [query, setQuery] = useState({ ticker: '', eventType: '', offset: 0, revision: 0 });
  const [result, setResult] = useState<CatalystResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const generation = useRef(0);

  function invalidate() {
    generation.current += 1;
    setResult(null);
    setError(null);
    setLoading(false);
  }
  function apply() {
    invalidate();
    setQuery(previous => ({ ticker: ticker.trim().toUpperCase(), eventType, offset: 0, revision: previous.revision + 1 }));
  }
  function page(offset: number) {
    invalidate();
    setQuery(previous => ({ ...previous, offset, revision: previous.revision + 1 }));
  }
  useEffect(() => {
    const request = ++generation.current;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setResult(null);
    fetchFinancialCatalysts(query.ticker, query.eventType, query.offset, controller.signal)
      .then(data => { if (request === generation.current) setResult(data); })
      .catch(err => { if (request === generation.current) setError(err instanceof Error ? err.message : 'Unable to read catalyst inbox.'); })
      .finally(() => { if (request === generation.current) setLoading(false); });
    return () => { generation.current += 1; controller.abort(); };
  }, [query]);

  const dirty = ticker.trim().toUpperCase() !== query.ticker || eventType !== query.eventType;
  const warnings = result ? catalystWarnings(result) : [];
  return <section className="financial-card catalyst-inbox" aria-labelledby="catalyst-heading">
    <h3 id="catalyst-heading">Company catalyst inbox</h3>
    <p>Research only · All stored evidence. Dashboard signal and transaction-value filters do not apply. No live provider calls or automated interpretation.</p>
    <form className="catalyst-controls" onSubmit={event => { event.preventDefault(); apply(); }}>
      <label>Ticker<input aria-label="Catalyst ticker" placeholder="All companies / global events" maxLength={32} value={ticker} onChange={event => { invalidate(); setTicker(event.target.value); }} /></label>
      <label>Event type<select aria-label="Catalyst event type" value={eventType} onChange={event => { invalidate(); setEventType(event.target.value); }}>
        <option value="">All stored types</option><option value="filing">Filings</option><option value="insider_trade">Insider transactions</option><option value="news">News</option><option value="calendar">Calendar</option>
      </select></label>
      <button type="submit">Apply</button>
      <button type="button" onClick={apply}>Refresh</button>
    </form>
    {dirty && <p role="status">Filters changed. Apply to read matching evidence.</p>}
    {!dirty && !loading && !result && !error && <p role="status">Apply or Refresh to read stored evidence.</p>}
    {loading && !dirty && <p role="status">Reading stored catalyst evidence…</p>}
    {error && <p role="alert" className="error-message">{error}</p>}
    {result && !dirty && <>
      <p className="catalyst-meta">Read at {result.retrieved_at} · This is API read time, not provider freshness or ingestion health.</p>
      {warnings.length > 0 && <aside className="catalyst-warnings" role="status"><strong>Partial dataset coverage</strong><ul>{warnings.map(warning => <li key={warning}>{warning}</li>)}</ul></aside>}
      {result.records.length === 0 && <p>No matching stored evidence on this page.{warnings.length ? ' Check dataset coverage above.' : ''}</p>}
      {[true, false].map(scheduled => {
        const records = result.records.filter(record => record.scheduled === scheduled);
        return records.length > 0 && <section key={String(scheduled)} aria-label={scheduled ? 'Upcoming scheduled events' : 'Observed and past events'}>
          <h4>{scheduled ? 'Upcoming · scheduled calendar events' : 'Observed / past · undated records last'}</h4>
          {records.map(record => <Evidence key={record.id} record={record} />)}
        </section>;
      })}
      <nav className="catalyst-pagination" aria-label="Catalyst pages">
        <button type="button" disabled={result.offset === 0} onClick={() => page(Math.max(0, result.offset - result.limit))}>Previous</button>
        <span>{result.count ? `${result.offset + 1}–${result.offset + result.count}` : '0'} of {result.total}</span>
        <button type="button" disabled={result.offset + result.limit >= result.total || result.offset + result.limit > 10000} onClick={() => page(result.offset + result.limit)}>Next</button>
      </nav>
      <p className="catalyst-meta">Pages are stable while the stored dataset is unchanged; ingestion can shift page boundaries.</p>
    </>}
  </section>;
}
