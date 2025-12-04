import { useState, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import type { CredentialsStatus, CredentialInfo } from '../types';
import { getCredentialsStatus, setCredential, deleteCredential } from '../api';
import './SettingsModal.css';

interface SettingsModalProps {
  onClose: () => void;
  onSaved?: () => void;
}

// Help URLs and placeholders for each credential type
const CREDENTIAL_CONFIG: Record<string, { placeholder: string; helpUrl: string; helpText: string }> = {
  anthropic_api_key: {
    placeholder: 'sk-ant-api...',
    helpUrl: 'https://console.anthropic.com/settings/keys',
    helpText: 'console.anthropic.com',
  },
  openai_api_key: {
    placeholder: 'sk-...',
    helpUrl: 'https://platform.openai.com/api-keys',
    helpText: 'platform.openai.com',
  },
  azure_openai_api_key: {
    placeholder: 'Your Azure OpenAI API key',
    helpUrl: 'https://portal.azure.com/',
    helpText: 'Azure Portal',
  },
  azure_openai_endpoint: {
    placeholder: 'https://your-resource.openai.azure.com/',
    helpUrl: 'https://portal.azure.com/',
    helpText: 'Azure Portal',
  },
  ollama_base_url: {
    placeholder: 'http://localhost:11434',
    helpUrl: 'https://ollama.ai/',
    helpText: 'ollama.ai',
  },
  vllm_base_url: {
    placeholder: 'http://localhost:8000',
    helpUrl: 'https://docs.vllm.ai/',
    helpText: 'docs.vllm.ai',
  },
};

interface CredentialCardProps {
  credential: CredentialInfo;
  saving: boolean;
  onSave: (key: string, value: string) => Promise<void>;
  onDelete: (key: string) => Promise<void>;
}

function CredentialCard({ credential, saving, onSave, onDelete }: CredentialCardProps) {
  const [keyValue, setKeyValue] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const config = CREDENTIAL_CONFIG[credential.key] || {
    placeholder: 'Enter value...',
    helpUrl: '#',
    helpText: 'documentation',
  };

  const handleSave = async () => {
    if (!keyValue.trim()) {
      setError('Please enter a value');
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      await onSave(credential.key, keyValue.trim());
      setKeyValue('');
      setSuccess('Saved successfully');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete ${credential.display_name}?`)) {
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      await onDelete(credential.key);
      setSuccess('Deleted');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete');
    }
  };

  // Determine if this is an API key or a URL type credential
  const isUrl = credential.key.includes('_url') || credential.key.includes('_endpoint');

  return (
    <div className="credential-card">
      <div className="credential-header">
        <span className="credential-name">{credential.display_name}</span>
        <span className={`credential-status ${credential.configured ? 'configured' : 'missing'}`}>
          {credential.configured
            ? `Configured (${credential.source === 'env' ? 'env var' : 'stored'})`
            : 'Not configured'}
        </span>
      </div>

      {/* Messages */}
      {error && (
        <div className="credential-message error">
          {error}
          <button onClick={() => setError(null)} className="dismiss">Dismiss</button>
        </div>
      )}
      {success && (
        <div className="credential-message success">
          {success}
          <button onClick={() => setSuccess(null)} className="dismiss">Dismiss</button>
        </div>
      )}

      {credential.configured && credential.masked_value && (
        <div className="credential-current">
          <span className="current-label">Current:</span>
          <code className="current-value">{credential.masked_value}</code>
          {credential.source === 'file' && (
            <button
              onClick={handleDelete}
              disabled={saving}
              className="button small danger"
            >
              Delete
            </button>
          )}
        </div>
      )}

      {credential.source === 'env' && (
        <p className="env-note">
          Currently using environment variable <code>{credential.env_var}</code>.
          You can still store a value below as a fallback.
        </p>
      )}

      <div className="credential-form">
        <div className="input-with-toggle">
          <input
            type={showKey || isUrl ? 'text' : 'password'}
            value={keyValue}
            onChange={(e) => setKeyValue(e.target.value)}
            placeholder={config.placeholder}
            className="key-input"
            disabled={saving}
          />
          {!isUrl && (
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="toggle-visibility"
              title={showKey ? 'Hide' : 'Show'}
            >
              {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          )}
        </div>
        <button
          onClick={handleSave}
          disabled={saving || !keyValue.trim()}
          className="button primary"
        >
          {saving ? 'Saving...' : credential.configured ? 'Update' : 'Save'}
        </button>
      </div>

      <p className="credential-help">
        {isUrl ? 'Configure your' : 'Get your API key from'}{' '}
        <a href={config.helpUrl} target="_blank" rel="noopener noreferrer">
          {config.helpText}
        </a>
      </p>
    </div>
  );
}

export function SettingsModal({ onClose, onSaved }: SettingsModalProps) {
  const [status, setStatus] = useState<CredentialsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load current status
  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCredentialsStatus();
      setStatus(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCredential = async (key: string, value: string) => {
    setSaving(true);
    try {
      await setCredential(key, value);
      await loadStatus();
      onSaved?.();
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCredential = async (key: string) => {
    setSaving(true);
    try {
      await deleteCredential(key);
      await loadStatus();
      onSaved?.();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-modal-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="settings-modal-header">
          <h2>Settings</h2>
          <button onClick={onClose} className="button small close-btn">X</button>
        </div>

        {/* Content */}
        <div className="settings-modal-content">
          {loading ? (
            <div className="settings-loading">Loading settings...</div>
          ) : (
            <>
              {/* Global error */}
              {error && (
                <div className="settings-message error">
                  {error}
                  <button onClick={() => setError(null)} className="dismiss">Dismiss</button>
                </div>
              )}

              {/* API Keys Section */}
              <section className="settings-section">
                <h3>API Keys & Configuration</h3>
                <p className="section-description">
                  Credentials are stored locally in <code>~/.amplifier-playground/credentials.json</code> with
                  restricted permissions. Environment variables take precedence over stored values.
                </p>

                {/* Dynamically render all credentials */}
                {status?.credentials.map((credential) => (
                  <CredentialCard
                    key={credential.key}
                    credential={credential}
                    saving={saving}
                    onSave={handleSaveCredential}
                    onDelete={handleDeleteCredential}
                  />
                ))}
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
