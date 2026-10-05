const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY;

async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (API_KEY) {
    headers.set('X-API-Key', API_KEY);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API request failed: ${res.status} ${res.statusText} - ${text}`);
  }
  return res.json();
}

export function fetchDashboard() {
  return fetchJson<{ summary: any }>('/api/v1/dashboard');
}

export function fetchTrends(query?: string) {
  const params = new URLSearchParams();
  params.set('limit', '20');
  if (query) {
    params.set('query', query);
  }
  return fetchJson<{ trends: any[] }>(`/api/v1/trends?${params.toString()}`);
}

export function fetchPlatforms() {
  return fetchJson<{ platforms: any[] }>('/api/v1/platforms');
}

export function fetchPipeline() {
  return fetchJson<{ pipeline: any }>('/api/v1/pipeline');
}

export function fetchSkills() {
  return fetchJson<{ skills: any[] }>('/api/v1/skills');
}

export function postResearch(payload: { skill_id: string; prompt: string; tickers?: string[]; context?: string }) {
  return fetchJson<{ request_id: string; status: string; skill_id: string; prompt: string; result: string; created_at: string }>('/api/v1/research', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function fetchSettings() {
  return fetchJson<{ feature_table: string; s3_bucket: string; platform_count: number; auth_enabled: boolean; api_base_url: string }>('/api/v1/settings');
}

export type FinancialRecord = Record<string, any>;

export type MoomooRecord = Record<string, unknown>;

export type MoomooResponse = {
  records: MoomooRecord[];
  count: number;
  retrieved_at: string;
};

export type MoomooHistoryPoint = { date: string; close: number };
export type MoomooHistoryResponse = {
  code: string;
  window: '1M' | '3M';
  start: string;
  end: string;
  adjustment: 'QFQ';
  series: MoomooHistoryPoint[];
  count: number;
  retrieved_at: string;
};

export function fetchMoomooHistory(code: string, window: '1M' | '3M') {
  const params = new URLSearchParams({ code, window });
  return fetchJson<MoomooHistoryResponse>(`/api/v1/moomoo/history?${params}`);
}

export function fetchMoomooQuotes(code: string) {
  const params = new URLSearchParams({ codes: code });
  return fetchJson<MoomooResponse>(`/api/v1/moomoo/quotes?${params}`);
}

export function fetchMoomooNews(keyword: string, maxCount = 10) {
  const params = new URLSearchParams({ keyword, max_count: String(maxCount) });
  return fetchJson<MoomooResponse>(`/api/v1/moomoo/news?${params}`);
}

export function fetchFinancialSummary() {
  return fetchJson<{ latest_filings: FinancialRecord[]; latest_insider_trades: FinancialRecord[]; latest_news: FinancialRecord[]; upcoming_events: FinancialRecord[]; counts: Record<string, number>; watchlist: string[] }>('/api/v1/financial/summary');
}

export function fetchFinancialFilings(ticker?: string, formType?: string) {
  const params = new URLSearchParams({ limit: '50' });
  if (ticker) params.set('ticker', ticker);
  if (formType) params.set('form_type', formType);
  return fetchJson<{ records: FinancialRecord[]; count: number }>(`/api/v1/financial/filings?${params}`);
}

export function fetchFinancialInsiderTrades(ticker?: string, signal?: string) {
  const params = new URLSearchParams({ limit: '50' });
  if (ticker) params.set('ticker', ticker);
  if (signal) params.set('signal', signal);
  return fetchJson<{ records: FinancialRecord[]; count: number }>(`/api/v1/financial/insider-trades?${params}`);
}

export function fetchFinancialNews(ticker?: string, signal?: string) {
  const params = new URLSearchParams({ limit: '50' });
  if (ticker) params.set('ticker', ticker);
  if (signal) params.set('signal', signal);
  return fetchJson<{ records: FinancialRecord[]; count: number }>(`/api/v1/financial/news?${params}`);
}

export function fetchFinancialCalendar(ticker?: string, eventType?: string) {
  const params = new URLSearchParams({ limit: '50' });
  if (ticker) params.set('ticker', ticker);
  if (eventType) params.set('event_type', eventType);
  return fetchJson<{ records: FinancialRecord[]; count: number }>(`/api/v1/financial/calendar?${params}`);
}

export type CatalystType = 'filing' | 'insider_trade' | 'news' | 'calendar';
export type CatalystRecord = {
  id: string;
  source_id: string | null;
  event_type: CatalystType;
  subtype: string | null;
  ticker: string | null;
  title: string;
  source: string | null;
  source_url: string | null;
  event_at: string | null;
  time_precision: 'timestamp' | 'date' | 'unknown';
  timezone: string | null;
  published_at: string | null;
  available_at: string | null;
  ingested_at: string | null;
  raw_event_at: unknown;
  scheduled: boolean;
  estimated: boolean | null;
  data_gaps: string[];
};
export type CatalystResponse = {
  records: CatalystRecord[];
  count: number;
  total: number;
  limit: number;
  offset: number;
  retrieved_at: string;
  dataset_status: Record<string, {
    status: 'loaded' | 'absent' | 'unreadable';
    rows_read: number;
    rows_skipped: number;
    duplicates_removed: number;
    records_loaded?: number;
    warning?: string;
  }>;
};

export function fetchFinancialCatalysts(ticker = '', eventType = '', offset = 0, signal?: AbortSignal) {
  const params = new URLSearchParams({ limit: '50', offset: String(offset) });
  if (ticker.trim()) params.set('ticker', ticker.trim().toUpperCase());
  if (eventType) params.set('event_type', eventType);
  return fetchJson<CatalystResponse>(`/api/v1/financial/catalysts?${params}`, { signal });
}
