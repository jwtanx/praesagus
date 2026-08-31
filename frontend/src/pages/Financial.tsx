import { useEffect, useState } from 'react';
import {
  fetchFinancialCalendar,
  fetchFinancialFilings,
  fetchFinancialInsiderTrades,
  fetchFinancialNews,
  fetchFinancialSummary,
  FinancialRecord,
} from '../services/api';

function value(record: FinancialRecord, key: string) {
  const item = record[key];
  return item === null || item === undefined || item === '' ? '—' : String(item);
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
