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
