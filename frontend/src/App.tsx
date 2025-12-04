import { useState, useEffect, useCallback } from 'react';
import { Settings, MessageSquare } from 'lucide-react';
import type { ProfileListItem, CredentialsStatus } from './types';
import { listProfiles, getCredentialsStatus } from './api';
import { SessionPane } from './components/SessionPane';
import { DependencyGraphViewer } from './components/DependencyGraphViewer';
import { HelpModal } from './components/HelpModal';
import { SettingsModal } from './components/SettingsModal';
import { ThemeToggle } from './components/ThemeToggle';
import './App.css';

interface Pane {
  id: string;
}

function App() {
  const [profiles, setProfiles] = useState<ProfileListItem[]>([]);
  const [panes, setPanes] = useState<Pane[]>([{ id: crypto.randomUUID() }]);
  const [error, setError] = useState<string | null>(null);
  const [viewingProfile, setViewingProfile] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [credentials, setCredentials] = useState<CredentialsStatus | null>(null);

  // Load profiles and credentials status on mount
  useEffect(() => {
    listProfiles()
      .then(setProfiles)
      .catch((e) => setError(e.message));

    loadCredentials();
  }, []);

  const loadCredentials = useCallback(() => {
    getCredentialsStatus()
      .then(setCredentials)
      .catch(console.error);
  }, []);

  const addPane = useCallback(() => {
    setPanes((prev) => [...prev, { id: crypto.randomUUID() }]);
  }, []);

  const removePane = useCallback((id: string) => {
    setPanes((prev) => {
      // Don't remove the last pane
      if (prev.length <= 1) return prev;
      return prev.filter((p) => p.id !== id);
    });
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div>
            <h1>Amplifier Playground</h1>
            <p className="subtitle">Build, test, and explore AI agent sessions</p>
          </div>
          <div className="header-actions">
            <span className="pane-count">{panes.length} pane{panes.length !== 1 ? 's' : ''}</span>
            <button onClick={addPane} className="button primary">
              + Add Pane
            </button>
            <ThemeToggle />
            <button
              onClick={() => setShowSettings(true)}
              className="button icon-btn secondary"
              title="Settings"
            >
              <Settings size={16} />
            </button>
            <a
              href="https://github.com/samueljklee/amplifier-playground/issues/new?template=feedback.md&title=[Feedback]%20"
              target="_blank"
              rel="noopener noreferrer"
              className="button icon-btn secondary"
              title="Send Feedback"
            >
              <MessageSquare size={16} />
            </a>
            <button onClick={() => setShowHelp(true)} className="button secondary">
              Help
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="global-error">
          Failed to load profiles: {error}
        </div>
      )}

      {/* Setup Banner - show if no credentials are configured */}
      {credentials && credentials.credentials.every(c => !c.configured) && (
        <div className="setup-banner">
          <span className="setup-banner-icon">!</span>
          <span className="setup-banner-text">
            <strong>API keys required:</strong> Configure at least one provider API key to start sessions.
          </span>
          <button onClick={() => setShowSettings(true)} className="button primary small">
            Configure
          </button>
        </div>
      )}

      <main className="panes-container">
        {panes.map((pane) => (
          <SessionPane
            key={pane.id}
            profiles={profiles}
            onClose={() => removePane(pane.id)}
            onViewProfile={setViewingProfile}
            onOpenSettings={() => setShowSettings(true)}
          />
        ))}
      </main>

      {/* Dependency Graph Viewer Modal */}
      {viewingProfile && (
        <DependencyGraphViewer
          profileName={viewingProfile}
          onClose={() => setViewingProfile(null)}
        />
      )}

      {/* Help Modal */}
      {showHelp && (
        <HelpModal onClose={() => setShowHelp(false)} />
      )}

      {/* Settings Modal */}
      {showSettings && (
        <SettingsModal
          onClose={() => setShowSettings(false)}
          onSaved={loadCredentials}
        />
      )}
    </div>
  );
}

export default App;
