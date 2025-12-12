import { useState, useEffect } from 'react';
import { api } from '../api';
import './Settings.css';

export default function Settings({ onClose }) {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadHealth();
  }, []);

  const loadHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const StatusIcon = ({ ready }) => (
    <span className={`status-icon ${ready ? 'ready' : 'not-ready'}`}>
      {ready ? '✓' : '✗'}
    </span>
  );

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Settings & Health Check</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="settings-content">
          {loading && <div className="loading">Checking configuration...</div>}

          {error && (
            <div className="error-box">
              <strong>Error:</strong> {error}
              <button onClick={loadHealth}>Retry</button>
            </div>
          )}

          {health && (
            <>
              <div className={`overall-status ${health.all_ready ? 'healthy' : 'degraded'}`}>
                <span className="status-label">System Status:</span>
                <span className="status-value">{health.all_ready ? 'All Ready' : 'Missing Configuration'}</span>
              </div>

              {!health.all_ready && (
                <div className="missing-config">
                  <h4>Missing Configuration:</h4>
                  <ul>
                    {health.council_models.filter(m => !m.ready).map((model, idx) => (
                      <li key={idx}>
                        <strong>{model.identifier}</strong>:
                        {model.type === 'cli'
                          ? ` CLI tool "${model.identifier.replace('cli:', '')}" not found in PATH`
                          : ` ${model.type.toUpperCase()}_API_KEY not set in .env`}
                      </li>
                    ))}
                    {!health.chairman_model.ready && (
                      <li>
                        <strong>Chairman ({health.chairman_model.identifier})</strong>:
                        {health.chairman_model.type === 'cli'
                          ? ` CLI tool not found in PATH`
                          : ` ${health.chairman_model.type.toUpperCase()}_API_KEY not set in .env`}
                      </li>
                    )}
                  </ul>
                </div>
              )}

              <section className="settings-section">
                <h3>API Keys</h3>
                <div className="config-list">
                  {Object.entries(health.api_keys).map(([provider, info]) => (
                    <div key={provider} className="config-item">
                      <StatusIcon ready={info.configured} />
                      <span className="config-name">{provider}</span>
                      <span className="config-value">
                        {info.configured ? info.key_preview : 'Not configured'}
                      </span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="settings-section">
                <h3>CLI Tools</h3>
                <div className="config-list">
                  {Object.entries(health.cli_tools).map(([name, info]) => (
                    <div key={name} className="config-item">
                      <StatusIcon ready={info.available} />
                      <span className="config-name">{name}</span>
                      <span className="config-value">
                        {info.available ? info.path : 'Not found in PATH'}
                      </span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="settings-section">
                <h3>Council Models</h3>
                <div className="config-list">
                  {health.council_models.map((model, idx) => (
                    <div key={idx} className="config-item">
                      <StatusIcon ready={model.ready} />
                      <span className="config-name">{model.identifier}</span>
                      <span className={`config-badge ${model.type}`}>{model.type}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="settings-section">
                <h3>Chairman Model</h3>
                <div className="config-list">
                  <div className="config-item">
                    <StatusIcon ready={health.chairman_model.ready} />
                    <span className="config-name">{health.chairman_model.identifier}</span>
                    <span className={`config-badge ${health.chairman_model.type}`}>
                      {health.chairman_model.type}
                    </span>
                  </div>
                </div>
              </section>

              <button className="refresh-btn" onClick={loadHealth}>
                Refresh Status
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
