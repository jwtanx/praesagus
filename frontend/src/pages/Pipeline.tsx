import { useEffect, useState } from 'react';
import { fetchPipeline } from '../services/api';

export default function Pipeline() {
  const [pipeline, setPipeline] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchPipeline()
      .then((result) => {
        setPipeline(result.pipeline);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-content">
      <div className="page-header">
        <h2>Pipeline Monitor</h2>
        <p>Review ingestion and processing pipeline state, including Airflow DAGs.</p>
      </div>

      {loading && <p>Loading pipeline status...</p>}
      {error && <p className="error-message">{error}</p>}

      <div className="pipeline-grid">
        <div className="pipeline-card">
          <h3>Pipeline Health</h3>
          <p>Status: {pipeline?.health ?? 'n/a'}</p>
          <p>Updated at: {pipeline?.updated_at ?? 'n/a'}</p>
        </div>
        <div className="pipeline-card">
          <h3>Scheduled DAGs</h3>
          <ul>
            {pipeline?.dags?.map((dag: any) => (
              <li key={dag.dag_id}>{dag.dag_id} – {dag.status} – next {dag.next_run}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
