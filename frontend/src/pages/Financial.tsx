import { useEffect, useState } from 'react';
import CatalystInbox from '../components/CatalystInbox';
import {
  fetchFinancialCalendar,
  fetchFinancialFilings,
  fetchFinancialInsiderTrades,
  fetchFinancialNews,
  fetchFinancialSummary,
  fetchMoomooNews,
  fetchMoomooQuotes,
  FinancialRecord,
  MoomooResponse,
} from '../services/api';

function value(record: FinancialRecord, key: string) {
  const item = record[key];
  return item === null || item === undefined || item === '' ? '—' : String(item);
}

function moomooValue(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const item = record[key];
    if (item !== null && item !== undefined && item !== '') {
      if (Array.isArray(item)) {
        return item.map((entry) => typeof entry === 'object' && entry !== null ? JSON.stringify(entry) : String(entry)).join(', ');
      }
      if (typeof item === 'object') return JSON.stringify(item);
      return String(item);
    }
  }
  return '—';
}

function externalUrl(record: Record<string, unknown>) {
  const candidate = moomooValue(record, ['url', 'link', 'news_url']);
  if (candidate === '—') return null;
  try {
    const url = new URL(candidate);
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null;
  } catch {
    return null;
  }
}

export default function Financial() {
  const [summary, setSummary] = useState<any>(null);
  const [ticker, setTicker] = useState('');
  const [signal, setSignal] = useState('');
  const [filings, setFilings] = useState<FinancialRecord[]>([]);
  const [insider, setInsider] = useState<FinancialRecord[]>([]);
  const [news, setNews] = useState<FinancialRecord[]>([]);
  const [calendar, setCalendar] = useState<FinancialRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [moomooCode, setMoomooCode] = useState('US.AAPL');
  const [quoteResult, setQuoteResult] = useState<{ code: string; data: MoomooResponse } | null>(null);
  const [moomooNewsResult, setMoomooNewsResult] = useState<{ code: string; data: MoomooResponse } | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [moomooNewsLoading, setMoomooNewsLoading] = useState(false);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [moomooNewsError, setMoomooNewsError] = useState<string | null>(null);

  function validatedMoomooCode() {
    const code = moomooCode.trim().toUpperCase();
    if (!/^[A-Z0-9]+\.[A-Z0-9._-]+$/.test(code)) {
      return null;
    }
    return code;
  }

  async function loadMoomooQuote() {
    const code = validatedMoomooCode();
    setQuoteResult(null);
    setQuoteError(code ? null : 'Enter a market-qualified code, such as US.AAPL.');
    if (!code) return;
    setQuoteLoading(true);
    try {
      setQuoteResult({ code, data: await fetchMoomooQuotes(code) });
    } catch (err: unknown) {
      setQuoteResult(null);
      setQuoteError(err instanceof Error ? err.message : 'Unable to fetch Moomoo quote.');
    } finally {
      setQuoteLoading(false);
    }
  }

  async function loadMoomooNews() {
    const code = validatedMoomooCode();
    setMoomooNewsResult(null);
    setMoomooNewsError(code ? null : 'Enter a market-qualified code, such as US.AAPL.');
    if (!code) return;
    setMoomooNewsLoading(true);
    try {
      const symbol = code.slice(code.indexOf('.') + 1);
      setMoomooNewsResult({ code, data: await fetchMoomooNews(symbol, 10) });
    } catch (err: unknown) {
      setMoomooNewsResult(null);
      setMoomooNewsError(err instanceof Error ? err.message : 'Unable to search Moomoo news.');
    } finally {
      setMoomooNewsLoading(false);
    }
  }

  async function loadData(selectedTicker = ticker, selectedSignal = signal) {
    setLoading(true);
    setError(null);
    try {
      const [overview, filingData, insiderData, newsData, calendarData] = await Promise.all([
        fetchFinancialSummary(),
        fetchFinancialFilings(selectedTicker),
        fetchFinancialInsiderTrades(selectedTicker, selectedSignal),
        fetchFinancialNews(selectedTicker, selectedSignal),
        fetchFinancialCalendar(selectedTicker),
      ]);
      setSummary(overview);
      setFilings(filingData.records);
      setInsider(insiderData.records);
      setNews(newsData.records);
      setCalendar(calendarData.records);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadData('', ''); }, []);

  return (
    <div className="page-content">
      <div className="page-header">
        <h2>Financial Intelligence</h2>
        <p>SEC filings, insider activity, earliest news signals, and upcoming events.</p>
      </div>

      <CatalystInbox />

      <div className="financial-filters">
        <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} placeholder="Ticker (for example AAPL)" />
        <select value={signal} onChange={(event) => setSignal(event.target.value)}>
          <option value="">All signals</option>
          <option value="buy">Buy</option>
          <option value="short">Short</option>
          <option value="watch">Watch</option>
        </select>
        <button type="button" onClick={() => void loadData()} disabled={loading}>Apply</button>
      </div>

      <section className="financial-card moomoo-panel" aria-labelledby="moomoo-heading">
        <h3 id="moomoo-heading">Moomoo OpenD (on demand)</h3>
        <p className="moomoo-description">Enter a market-qualified code. Quotes are request-time snapshots, not a stream. News uses request/response search; nothing is polled automatically. Provider market time may be exchange-local; retrieval time is UTC.</p>
        <div className="moomoo-controls">
          <label htmlFor="moomoo-code">Market-qualified code</label>
          <input
            id="moomoo-code"
            value={moomooCode}
            onChange={(event) => setMoomooCode(event.target.value)}
            placeholder="US.AAPL"
            autoComplete="off"
          />
          <button type="button" onClick={() => void loadMoomooQuote()} disabled={quoteLoading}>
            {quoteLoading ? 'Fetching quote…' : 'Fetch quote snapshot'}
          </button>
          <button type="button" onClick={() => void loadMoomooNews()} disabled={moomooNewsLoading}>
            {moomooNewsLoading ? 'Searching news…' : 'Search news'}
          </button>
        </div>
        <div className="moomoo-results">
          <section aria-labelledby="moomoo-quote-heading">
            <h4 id="moomoo-quote-heading">Quote snapshot</h4>
            {quoteError && <p className="error-message" role="alert">{quoteError}</p>}
            {quoteLoading && <p role="status">Requesting latest quote snapshot…</p>}
            {!quoteLoading && !quoteError && !quoteResult && <p>Fetch a quote to view a request-time snapshot.</p>}
            {quoteResult && !quoteLoading && !quoteError && <>
              <p className="moomoo-meta">Requested for {quoteResult.code} · Retrieved {quoteResult.data.retrieved_at || '—'}</p>
              {quoteResult.data.records.length === 0 ? <p>No quote records returned.</p> : quoteResult.data.records.map((record, index) => (
                <div className="moomoo-record" key={`${moomooValue(record, ['code'])}-${index}`}>
                  <strong>{moomooValue(record, ['name', 'code'])}</strong>
                  <span>Source: Moomoo OpenD</span>
                  <dl className="moomoo-quote-fields">
                    {[
                      ['Last price', ['last_price']], ['Market time', ['data_time', 'update_time']],
                      ['Open', ['open_price']], ['High', ['high_price']], ['Low', ['low_price']],
                      ['Previous close', ['prev_close_price']], ['Volume', ['volume']], ['Turnover', ['turnover']],
                    ].map(([label, fields]) => {
                      const shown = moomooValue(record, fields as string[]);
                      return shown === '—' ? null : <div key={label as string}><dt>{label as string}</dt><dd>{shown}</dd></div>;
                    })}
                  </dl>
                </div>
              ))}
            </>}
          </section>
          <section aria-labelledby="moomoo-news-heading">
            <h4 id="moomoo-news-heading">Moomoo news · max 10</h4>
            {moomooNewsError && <p className="error-message" role="alert">{moomooNewsError}</p>}
            {moomooNewsLoading && <p role="status">Searching Moomoo news…</p>}
            {!moomooNewsLoading && !moomooNewsError && !moomooNewsResult && <p>Search news to view recent results for this symbol.</p>}
            {moomooNewsResult && !moomooNewsLoading && !moomooNewsError && <>
              <p className="moomoo-meta">Search: {moomooNewsResult.code} · Retrieved {moomooNewsResult.data.retrieved_at || '—'}</p>
              {moomooNewsResult.data.records.length === 0 ? <p>No Moomoo news records returned.</p> : moomooNewsResult.data.records.map((record, index) => {
                const url = externalUrl(record);
                const returnedTitle = moomooValue(record, ['title', 'news_title', 'name']);
                const title = returnedTitle === '—' ? 'Untitled Moomoo news item' : returnedTitle;
                const returnedSource = moomooValue(record, ['source', 'provider', 'media_name']);
                return <article className="moomoo-record" key={`${title}-${index}`}>
                  <strong>{url ? <a href={url} target="_blank" rel="noreferrer">{title}</a> : title}</strong>
                  <span>Source: {returnedSource === '—' ? 'Moomoo' : returnedSource}</span>
                  <span>Published: {moomooValue(record, ['publish_time', 'published_at', 'pub_time', 'pub_date_time', 'time'])}</span>
                  <span>Type: {moomooValue(record, ['news_sub_type'])}</span>
                  <span>Related securities: {moomooValue(record, ['related_securities'])}</span>
                  <span>Views: {moomooValue(record, ['view_count'])}</span>
                  {url && <a className="moomoo-external-link" href={url} target="_blank" rel="noreferrer">Open source ↗</a>}
                </article>;
              })}
            </>}
          </section>
        </div>
      </section>

      {loading && <p>Loading financial data...</p>}
      {error && <p className="error-message">{error}</p>}

      <div className="financial-stats">
        {['filings', 'insider_trades', 'news', 'calendar', 'buy_signals', 'short_signals'].map((key) => (
          <div className="stat-card" key={key}><span>{summary?.counts?.[key] ?? '—'}</span><p>{key.replace(/_/g, ' ')}</p></div>
        ))}
      </div>

      <div className="financial-grid">
        <section className="financial-card"><h3>Latest filings</h3>{filings.slice(0, 8).map((item, index) => <a className="financial-row" href={item.document_url || item.filing_url} target="_blank" rel="noreferrer" key={`${item.source_id || item.accession_number}-${index}`}><strong>{value(item, 'ticker')} · {value(item, 'form_type')}</strong><span>{value(item, 'filing_date')}</span></a>)}{!filings.length && <p>No filing records.</p>}</section>
        <section className="financial-card"><h3>Insider activity</h3>{insider.slice(0, 8).map((item, index) => <div className="financial-row" key={`${item.source_id}-${index}`}><strong>{value(item, 'ticker')} · {value(item, 'reporting_owner_name')}</strong><span className={`signal-${value(item, 'signal')}`}>{value(item, 'signal')} · ${value(item, 'transaction_value')}</span></div>)}{!insider.length && <p>No insider records.</p>}</section>
        <section className="financial-card"><h3>News signals</h3>{news.slice(0, 8).map((item, index) => <a className="financial-row" href={item.link} target="_blank" rel="noreferrer" key={`${item.source_id}-${index}`}><strong>{value(item, 'ticker')} · {value(item, 'title')}</strong><span className={`signal-${value(item, 'signal')}`}>{value(item, 'signal')} · {value(item, 'published_at')}</span></a>)}{!news.length && <p>No news records.</p>}</section>
        <section className="financial-card"><h3>Calendar</h3>{calendar.slice(0, 8).map((item, index) => <div className="financial-row" key={`${item.source_id}-${index}`}><strong>{value(item, 'event_date')} · {value(item, 'title')}</strong><span>{value(item, 'impact')}</span></div>)}{!calendar.length && <p>No calendar records.</p>}</section>
      </div>
    </div>
  );
}
