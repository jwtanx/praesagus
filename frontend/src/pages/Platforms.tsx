import { useEffect, useState } from 'react';
import { fetchPlatforms } from '../services/api';

export default function Platforms() {
  const [platforms, setPlatforms] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchPlatforms()
      .then((result) => {
        setPlatforms(result.platforms);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-content">
      <div className="page-header">
        <h2>Platform Feeds</h2>
        <p>Monitor ingestion status and source health across connected platforms.</p>
      </div>

      {loading && <p>Loading platform status...</p>}
      {error && <p className="error-message">{error}</p>}

      <div className="platform-grid">
        {platforms.map((platform) => (
          <div key={platform.name} className="platform-card">
            <div>
              <h3>{platform.label}</h3>
              <p>{platform.items_ingested} items ingested</p>
            </div>
            <span className={`status-badge ${platform.status.toLowerCase()}`}>{platform.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
