import { useState, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import type { CredentialsStatus } from '../types';
import { getCredentialsStatus, setAnthropicKey, deleteAnthropicKey } from '../api';
import './SettingsModal.css';

interface SettingsModalProps {
  onClose: () => void;
  onSaved?: () => void;
}

export function SettingsModal({ onClose, onSaved }: SettingsModalProps) {
  const [status, setStatus] = useState<CredentialsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Anthropic key form state
  const [anthropicKey, setAnthropicKey_] = useState('');
  const [showAnthropicKey, setShowAnthropicKey] = useState(false);

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

  const handleSaveAnthropicKey = async () => {
    if (!anthropicKey.trim()) {
      setError('Please enter an API key');
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await setAnthropicKey(anthropicKey.trim());
      setAnthropicKey_('');
      setSuccess('API key saved successfully');
      await loadStatus();
      onSaved?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save API key');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAnthropicKey = async () => {
    if (!confirm('Are you sure you want to delete the stored API key?')) {
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await deleteAnthropicKey();
      setSuccess('API key deleted');
      await loadStatus();
      onSaved?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete API key');
    } finally {
      setSaving(false);
    }
  };

  const anthropicStatus = status?.anthropic_api_key;

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
              {/* Messages */}
              {error && (
                <div className="settings-message error">
                  {error}
                  <button onClick={() => setError(null)} className="dismiss">Dismiss</button>
                </div>
              )}
              {success && (
                <div className="settings-message success">
                  {success}
                  <button onClick={() => setSuccess(null)} className="dismiss">Dismiss</button>
                </div>
              )}

              {/* API Keys Section */}
              <section className="settings-section">
                <h3>API Keys</h3>
                <p className="section-description">
                  API keys are stored locally in <code>~/.amplifier/credentials.json</code> with
                  restricted permissions. Environment variables take precedence over stored keys.
                </p>

                {/* Anthropic API Key */}
                <div className="credential-card">
                  <div className="credential-header">
                    <span className="credential-name">Anthropic API Key</span>
                    <span className={`credential-status ${anthropicStatus?.configured ? 'configured' : 'missing'}`}>
                      {anthropicStatus?.configured
                        ? `Configured (${anthropicStatus.source === 'env' ? 'env var' : 'stored'})`
                        : 'Not configured'}
                    </span>
                  </div>

                  {anthropicStatus?.configured && anthropicStatus.masked_value && (
                    <div className="credential-current">
                      <span className="current-label">Current:</span>
                      <code className="current-value">{anthropicStatus.masked_value}</code>
                      {anthropicStatus.source === 'file' && (
                        <button
                          onClick={handleDeleteAnthropicKey}
                          disabled={saving}
                          className="button small danger"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  )}

                  {anthropicStatus?.source === 'env' ? (
                    <p className="env-note">
                      Using environment variable <code>ANTHROPIC_API_KEY</code>.
                      Unset the env var to use a stored key instead.
                    </p>
                  ) : (
                    <div className="credential-form">
                      <div className="input-with-toggle">
                        <input
                          type={showAnthropicKey ? 'text' : 'password'}
                          value={anthropicKey}
                          onChange={(e) => setAnthropicKey_(e.target.value)}
                          placeholder="sk-ant-api..."
                          className="key-input"
                          disabled={saving}
                        />
                        <button
                          type="button"
                          onClick={() => setShowAnthropicKey(!showAnthropicKey)}
                          className="toggle-visibility"
                          title={showAnthropicKey ? 'Hide' : 'Show'}
                        >
                          {showAnthropicKey ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                      <button
                        onClick={handleSaveAnthropicKey}
                        disabled={saving || !anthropicKey.trim()}
                        className="button primary"
                      >
                        {saving ? 'Saving...' : anthropicStatus?.configured ? 'Update Key' : 'Save Key'}
                      </button>
                    </div>
                  )}

                  <p className="credential-help">
                    Get your API key from{' '}
                    <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer">
                      console.anthropic.com
                    </a>
                  </p>
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
