import { useState, useEffect } from 'react';
import type { SessionDetailInfo } from '../types';
import { getSessionDetails } from '../api';
import './SessionInfoModal.css';

interface SessionInfoModalProps {
  sessionId: string;
  onClose: () => void;
}

type InfoSection = 'overview' | 'mount_plan' | 'session' | 'providers' | 'tools' | 'hooks' | 'agents';

interface SectionInfo {
  key: InfoSection;
  label: string;
  available: boolean;
}

function getSections(details: SessionDetailInfo | null): SectionInfo[] {
  const mountPlan = details?.mount_plan as Record<string, unknown> | null;
  const agents = mountPlan?.agents as Record<string, unknown> | undefined;
  return [
    { key: 'overview', label: 'Overview', available: true },
    { key: 'session', label: 'Session Config', available: !!mountPlan?.session },
    { key: 'providers', label: 'Providers', available: Array.isArray(mountPlan?.providers) && (mountPlan?.providers as unknown[]).length > 0 },
    { key: 'tools', label: 'Tools', available: Array.isArray(mountPlan?.tools) && (mountPlan?.tools as unknown[]).length > 0 },
    { key: 'hooks', label: 'Hooks', available: Array.isArray(mountPlan?.hooks) && (mountPlan?.hooks as unknown[]).length > 0 },
    { key: 'agents', label: 'Agents', available: !!agents && Object.keys(agents).length > 0 },
    { key: 'mount_plan', label: 'Full Mount Plan', available: !!mountPlan },
  ];
}

function copyToClipboard(text: string): void {
  navigator.clipboard.writeText(text).catch(console.error);
}

export function SessionInfoModal({ sessionId, onClose }: SessionInfoModalProps) {
  const [details, setDetails] = useState<SessionDetailInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<InfoSection>('overview');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    getSessionDetails(sessionId)
      .then(setDetails)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

  const handleCopy = (field: string, value: string) => {
    copyToClipboard(value);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 1500);
  };

  const sections = getSections(details);
  const mountPlan = details?.mount_plan as Record<string, unknown> | null;

  const renderSectionContent = () => {
    if (!details) return null;

    switch (selectedSection) {
      case 'overview':
        return (
          <div className="info-section">
            <h3>Session Overview</h3>
            <div className="info-grid">
              <div className="info-row">
                <span className="info-label">Session ID</span>
                <span className="info-value monospace">
                  {details.session_id}
                  <button
                    className="copy-btn"
                    onClick={() => handleCopy('session_id', details.session_id)}
                    title="Copy to clipboard"
                  >
                    {copiedField === 'session_id' ? '✓' : 'Copy'}
                  </button>
                </span>
              </div>
              <div className="info-row">
                <span className="info-label">Status</span>
                <span className={`info-value status-badge ${details.is_running ? 'running' : 'stopped'}`}>
                  {details.is_running ? 'Running' : 'Stopped'}
                </span>
              </div>
              <div className="info-row">
                <span className="info-label">Profile</span>
                <span className="info-value">{details.profile || '—'}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Approval Mode</span>
                <span className="info-value">{details.approval_mode || 'auto'}</span>
              </div>
              {details.config_id && (
                <div className="info-row">
                  <span className="info-label">Config ID</span>
                  <span className="info-value monospace">{details.config_id}</span>
                </div>
              )}
              {details.parent_session_id && (
                <div className="info-row">
                  <span className="info-label">Parent Session</span>
                  <span className="info-value monospace">{details.parent_session_id}</span>
                </div>
              )}
            </div>
          </div>
        );

      case 'session':
        const sessionConfig = mountPlan?.session as Record<string, unknown> | undefined;
        return (
          <div className="info-section">
            <h3>Session Configuration</h3>
            {sessionConfig ? (
              <pre className="json-content">{JSON.stringify(sessionConfig, null, 2)}</pre>
            ) : (
              <p className="empty-note">No session configuration available</p>
            )}
          </div>
        );

      case 'providers':
        const providers = mountPlan?.providers as unknown[] | undefined;
        return (
          <div className="info-section">
            <h3>Providers ({providers?.length || 0})</h3>
            {providers && providers.length > 0 ? (
              <div className="item-list">
                {providers.map((p, i) => {
                  const provider = p as Record<string, unknown>;
                  return (
                    <div key={i} className="list-item">
                      <div className="list-item-header">
                        <span className="item-badge provider">Provider</span>
                        <span className="item-name">{String(provider.module || 'Unknown')}</span>
                      </div>
                      <pre className="json-content small">{JSON.stringify(provider, null, 2)}</pre>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="empty-note">No providers configured</p>
            )}
          </div>
        );

      case 'tools':
        const tools = mountPlan?.tools as unknown[] | undefined;
        return (
          <div className="info-section">
            <h3>Tools ({tools?.length || 0})</h3>
            {tools && tools.length > 0 ? (
              <div className="item-list">
                {tools.map((t, i) => {
                  const tool = t as Record<string, unknown>;
                  return (
                    <div key={i} className="list-item">
                      <div className="list-item-header">
                        <span className="item-badge tool">Tool</span>
                        <span className="item-name">{String(tool.module || 'Unknown')}</span>
                      </div>
                      <pre className="json-content small">{JSON.stringify(tool, null, 2)}</pre>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="empty-note">No tools configured</p>
            )}
          </div>
        );

      case 'hooks':
        const hooks = mountPlan?.hooks as unknown[] | undefined;
        return (
          <div className="info-section">
            <h3>Hooks ({hooks?.length || 0})</h3>
            {hooks && hooks.length > 0 ? (
              <div className="item-list">
                {hooks.map((h, i) => {
                  const hook = h as Record<string, unknown>;
                  return (
                    <div key={i} className="list-item">
                      <div className="list-item-header">
                        <span className="item-badge hook">Hook</span>
                        <span className="item-name">{String(hook.module || 'Unknown')}</span>
                      </div>
                      <pre className="json-content small">{JSON.stringify(hook, null, 2)}</pre>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="empty-note">No hooks configured</p>
            )}
          </div>
        );

      case 'agents':
        const agents = mountPlan?.agents as Record<string, unknown> | undefined;
        const agentEntries = agents ? Object.entries(agents) : [];
        return (
          <div className="info-section">
            <h3>Agents ({agentEntries.length})</h3>
            {agentEntries.length > 0 ? (
              <div className="item-list">
                {agentEntries.map(([name, config]) => {
                  return (
                    <div key={name} className="list-item">
                      <div className="list-item-header">
                        <span className="item-badge agent">Agent</span>
                        <span className="item-name">{name}</span>
                      </div>
                      <pre className="json-content small">{JSON.stringify(config, null, 2)}</pre>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="empty-note">No agents configured</p>
            )}
          </div>
        );

      case 'mount_plan':
        return (
          <div className="info-section">
            <h3>
              Full Mount Plan
              <button
                className="copy-btn header-copy"
                onClick={() => handleCopy('mount_plan', JSON.stringify(mountPlan, null, 2))}
                title="Copy to clipboard"
              >
                {copiedField === 'mount_plan' ? '✓ Copied' : 'Copy JSON'}
              </button>
            </h3>
            {mountPlan ? (
              <pre className="json-content">{JSON.stringify(mountPlan, null, 2)}</pre>
            ) : (
              <p className="empty-note">No mount plan available</p>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="session-info-overlay" onClick={onClose}>
      <div className="session-info-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="session-info-header">
          <div>
            <h2>Session Info</h2>
            <p className="session-info-subtitle">
              {details?.profile || 'Session'} • {details?.session_id.slice(0, 8)}...
            </p>
          </div>
          <button onClick={onClose} className="button small close-btn">X</button>
        </div>

        {/* Main content area */}
        <div className="session-info-body">
          {loading && (
            <div className="session-info-loading">Loading session details...</div>
          )}

          {error && (
            <div className="session-info-error">{error}</div>
          )}

          {details && !loading && (
            <>
              {/* Sidebar navigation */}
              <div className="session-info-sidebar">
                <div className="sidebar-header">Sections</div>
                <div className="sidebar-nav">
                  {sections.filter(s => s.available).map((section) => (
                    <button
                      key={section.key}
                      className={`sidebar-nav-item ${selectedSection === section.key ? 'selected' : ''}`}
                      onClick={() => setSelectedSection(section.key)}
                    >
                      {section.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Content panel */}
              <div className="session-info-content">
                {renderSectionContent()}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
