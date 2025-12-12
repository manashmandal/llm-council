import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''} ${resp.error ? 'error' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {resp.model.split('/')[1] || resp.model}
            {resp.error && ' ⚠'}
          </button>
        ))}
      </div>

      <div className={`tab-content ${responses[activeTab].error ? 'error-content' : ''}`}>
        <div className="model-name">{responses[activeTab].model}</div>
        {responses[activeTab].error ? (
          <div className="error-text">{responses[activeTab].response}</div>
        ) : (
          <div className="response-text markdown-content">
            <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
