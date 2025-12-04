import { useState, useEffect, useCallback } from 'react';
import type { ProfileListItem } from './types';
import { listProfiles } from './api';
import { SessionPane } from './components/SessionPane';
import { DependencyGraphViewer } from './components/DependencyGraphViewer';
import { HelpModal } from './components/HelpModal';
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

  // Load profiles on mount
  useEffect(() => {
    listProfiles()
      .then(setProfiles)
      .catch((e) => setError(e.message));
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

      <main className="panes-container">
        {panes.map((pane) => (
          <SessionPane
            key={pane.id}
            profiles={profiles}
            onClose={() => removePane(pane.id)}
            onViewProfile={setViewingProfile}
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
    </div>
  );
}

export default App;
