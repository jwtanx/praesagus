import { useEffect, useState } from 'react';
import { fetchSettings } from '../services/api';

export default function Settings() {
  const [settings, setSettings] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSettings()
      .then((result) => setSettings(result))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="page-content">
      <div className="page-header">
        <h2>Settings</h2>
        <p>Configure frontend preferences and service endpoints.</p>
      </div>

      {error && <p className="error-message">{error}</p>}

      <div className="settings-panel">
        <div className="settings-card">
          <h3>API Endpoint</h3>
          <p>http://localhost:8000</p>
        </div>
        <div className="settings-card">
          <h3>Feature Store</h3>
          <p>{settings?.feature_table ?? 'Loading...'}</p>
        </div>
        <div className="settings-card">
          <h3>S3 Bucket</h3>
          <p>{settings?.s3_bucket ?? 'Loading...'}</p>
        </div>
        <div className="settings-card">
          <h3>Platforms</h3>
          <p>{settings?.platform_count ?? 'Loading...'}</p>
        </div>
        <div className="settings-card">
          <h3>Auth Enabled</h3>
          <p>{settings?.auth_enabled ? 'Yes' : 'No'}</p>
        </div>
      </div>
    </div>
  );
}
