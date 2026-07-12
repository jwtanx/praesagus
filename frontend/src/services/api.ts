const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
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
  return fetchJson<{ feature_table: string; s3_bucket: string; platform_count: number; auth_enabled: boolean }>('/api/v1/settings');
}
