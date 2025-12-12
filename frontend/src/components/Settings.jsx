import { useState, useEffect } from 'react';
import { api } from '../api';
import './Settings.css';

export default function Settings({ onClose }) {
  const [health, setHealth] = useState(null);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [editMode, setEditMode] = useState(false);

  // Editable state
  const [councilModels, setCouncilModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState('');
  const [newModel, setNewModel] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, configData] = await Promise.all([
        api.getHealth(),
        api.getConfig()
      ]);
      setHealth(healthData);
      setConfig(configData);
      setCouncilModels(configData.council_models);
      setChairmanModel(configData.chairman_model);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.updateConfig(councilModels, chairmanModel);
      await loadData();
      setEditMode(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setCouncilModels(config.council_models);
    setChairmanModel(config.chairman_model);
    setEditMode(false);
  };

  const addModel = () => {
    if (newModel.trim() && !councilModels.includes(newModel.trim())) {
      setCouncilModels([...councilModels, newModel.trim()]);
      setNewModel('');
    }
  };

  const removeModel = (index) => {
    setCouncilModels(councilModels.filter((_, i) => i !== index));
  };

  const StatusIcon = ({ ready }) => (
    <span className={`status-icon ${ready ? 'ready' : 'not-ready'}`}>
      {ready ? '✓' : '✗'}
    </span>
  );

  // Available model options for quick add
  const modelOptions = [
    { value: 'cli:codex', label: 'Codex CLI (GPT-5.2)' },
    { value: 'cli:gemini', label: 'Gemini CLI' },
    { value: 'cli:claude', label: 'Claude CLI' },
    { value: 'anthropic/claude-opus-4-5-20251101', label: 'Claude Opus 4.5 (API)' },
    { value: 'anthropic/claude-sonnet-4-20250514', label: 'Claude Sonnet 4 (API)' },
    { value: 'openai/gpt-5.2', label: 'GPT-5.2 (API)' },
    { value: 'openai/gpt-4o', label: 'GPT-4o (API)' },
    { value: 'openrouter:google/gemini-3-pro-preview', label: 'Gemini 3 Pro (OpenRouter)' },
    { value: 'openrouter:x-ai/grok-4', label: 'Grok 4 (OpenRouter)' },
  ];

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Settings & Health Check</h2>
          <button className="close-btn" onClick={onClose}>x</button>
        </div>

        <div className="settings-content">
          {loading && <div className="loading">Loading configuration...</div>}

          {error && (
            <div className="error-box">
              <strong>Error:</strong> {error}
              <button onClick={loadData}>Retry</button>
            </div>
          )}

          {health && config && (
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

              {/* Council Configuration */}
              <section className="settings-section">
                <div className="section-header">
                  <h3>Council Models</h3>
                  {!editMode && (
                    <button className="edit-btn" onClick={() => setEditMode(true)}>Edit</button>
                  )}
                </div>

                {editMode ? (
                  <div className="edit-models">
                    {councilModels.map((model, idx) => (
                      <div key={idx} className="editable-model">
                        <span>{model}</span>
                        <button className="remove-btn" onClick={() => removeModel(idx)}>x</button>
                      </div>
                    ))}
                    <div className="add-model">
                      <select
                        value={newModel}
                        onChange={(e) => setNewModel(e.target.value)}
                      >
                        <option value="">Select a model...</option>
                        {modelOptions
                          .filter(opt => !councilModels.includes(opt.value))
                          .map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                      </select>
                      <button className="add-btn" onClick={addModel} disabled={!newModel}>Add</button>
                    </div>
                  </div>
                ) : (
                  <div className="config-list">
                    {health.council_models.map((model, idx) => (
                      <div key={idx} className="config-item">
                        <StatusIcon ready={model.ready} />
                        <span className="config-name">{model.identifier}</span>
                        <span className={`config-badge ${model.type}`}>{model.type}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Chairman Configuration */}
              <section className="settings-section">
                <h3>Chairman Model</h3>
                {editMode ? (
                  <select
                    className="chairman-select"
                    value={chairmanModel}
                    onChange={(e) => setChairmanModel(e.target.value)}
                  >
                    {modelOptions.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                ) : (
                  <div className="config-list">
                    <div className="config-item">
                      <StatusIcon ready={health.chairman_model.ready} />
                      <span className="config-name">{health.chairman_model.identifier}</span>
                      <span className={`config-badge ${health.chairman_model.type}`}>
                        {health.chairman_model.type}
                      </span>
                    </div>
                  </div>
                )}
              </section>

              {editMode && (
                <div className="edit-actions">
                  <button className="cancel-btn" onClick={handleCancel}>Cancel</button>
                  <button className="save-btn" onClick={handleSave} disabled={saving || councilModels.length === 0}>
                    {saving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              )}

              {/* API Keys */}
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

              {/* CLI Tools */}
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

              <button className="refresh-btn" onClick={loadData}>
                Refresh Status
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
