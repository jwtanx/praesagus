import { useEffect, useState } from 'react';
import { fetchTrends } from '../services/api';

export default function Trends() {
  const [trends, setTrends] = useState<any[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchTrends()
      .then((result) => {
        setTrends(result.trends);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  function handleSearch() {
    setLoading(true);
    fetchTrends(query)
      .then((result) => {
        setTrends(result.trends);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <h2>Trends Explorer</h2>
        <p>Browse current trend signals with filters and score insights.</p>
      </div>

      <div className="trend-search">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by entity or source"
        />
        <button type="button" onClick={handleSearch}>
          Search
        </button>
      </div>

      {loading && <p>Loading trends...</p>}
      {error && <p className="error-message">{error}</p>}

      <div className="cards-grid">
        {trends.map((trend) => (
          <div key={trend.entity} className="trend-card">
            <div className="trend-card-header">
              <h3>{trend.entity}</h3>
              <span className="trend-score">{trend.score?.toFixed?.(2) ?? trend.score}</span>
            </div>
            <p>{trend.evidence?.length ?? 0} evidence sources</p>
            <div className="trend-tags">
              <span>Mentions: {trend.mention_count}</span>
              <span>Last seen: {trend.last_seen ?? 'n/a'}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
