import { useState, useEffect, useRef, useCallback } from 'react';
import { Info, FileJson, AlertTriangle } from 'lucide-react';
import type { ProfileListItem, SessionInfo, Message } from '../types';
import { createSession, sendPrompt, stopSession, subscribeToEvents, getProfileCredentials, type ProfileCredentials } from '../api';
import { SessionInfoModal } from './SessionInfoModal';
import { MountPlanInputModal } from './MountPlanInputModal';

const CUSTOM_JSON_VALUE = '__custom_json__';

interface SessionPaneProps {
  profiles: ProfileListItem[];
  onClose: () => void;
  onViewProfile: (profileName: string) => void;
  onOpenSettings?: () => void;
}

export function SessionPane({ profiles, onClose, onViewProfile, onOpenSettings }: SessionPaneProps) {
  const [selectedProfile, setSelectedProfile] = useState<string>('');
  const [customMountPlan, setCustomMountPlan] = useState<Record<string, unknown> | null>(null);
  const [showMountPlanInput, setShowMountPlanInput] = useState(false);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<Array<{ event: string; data: unknown }>>([]);
  const [showEvents, setShowEvents] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [credentialStatus, setCredentialStatus] = useState<ProfileCredentials | null>(null);

  // Check credentials when profile changes
  useEffect(() => {
    if (!selectedProfile || selectedProfile === CUSTOM_JSON_VALUE) {
      setCredentialStatus(null);
      return;
    }

    getProfileCredentials(selectedProfile)
      .then(setCredentialStatus)
      .catch((err) => {
        console.error('Failed to check credentials:', err);
        setCredentialStatus(null);
      });
  }, [selectedProfile]);

  // Derived state: whether we have a valid session config
  const hasValidConfig = selectedProfile && selectedProfile !== CUSTOM_JSON_VALUE
    ? true
    : customMountPlan !== null;

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Subscribe to session events
  useEffect(() => {
    if (!session) return;

    const unsubscribe = subscribeToEvents(
      session.session_id,
      (event, data) => {
        setEvents((prev) => [...prev, { event, data }]);
      },
      (err) => {
        console.error('Event stream error:', err);
      }
    );

    return () => unsubscribe();
  }, [session]);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-scroll events
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const handleStopSession = useCallback(async () => {
    if (!session) return;

    setLoading(true);
    try {
      await stopSession(session.session_id);
      setSession(null);
      setMessages((prev) => [
        ...prev,
        { role: 'system', content: 'Session stopped', timestamp: new Date() },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to stop session');
    } finally {
      setLoading(false);
    }
  }, [session]);

  const handleSend = useCallback(async () => {
    if (!input.trim()) return;
    if (!hasValidConfig) {
      setError('Please select a profile or configure a custom mount plan');
      return;
    }

    const userMessage = input.trim();
    setInput('');
    setLoading(true);
    setError(null);

    try {
      // Auto-start session if not already started
      let currentSession = session;
      if (!currentSession) {
        setMessages([]);
        setEvents([]);

        // Create session with profile or custom mount plan
        const isCustom = selectedProfile === CUSTOM_JSON_VALUE && customMountPlan;
        if (isCustom) {
          currentSession = await createSession({ mountPlan: customMountPlan });
        } else {
          currentSession = await createSession({ profile: selectedProfile });
        }

        setSession(currentSession);
        setMessages([
          {
            role: 'system',
            content: isCustom
              ? 'Session started with custom mount plan'
              : `Session started with profile: ${selectedProfile}`,
            timestamp: new Date(),
          },
        ]);
      }

      // Add user message to display
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: userMessage, timestamp: new Date() },
      ]);

      // Send the message
      const response = await sendPrompt(currentSession.session_id, userMessage);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.response, timestamp: new Date() },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to send message');
    } finally {
      setLoading(false);
    }
  }, [session, input, selectedProfile, customMountPlan, hasValidConfig]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="session-pane">
      {/* Pane Header */}
      <div className="pane-header">
        <select
          value={selectedProfile}
          onChange={(e) => {
            const value = e.target.value;
            setSelectedProfile(value);
            if (value === CUSTOM_JSON_VALUE) {
              setShowMountPlanInput(true);
            } else {
              setCustomMountPlan(null);
            }
          }}
          disabled={!!session || loading}
          className="profile-select-inline"
        >
          <option value="">Select configuration...</option>
          <option value={CUSTOM_JSON_VALUE}>Paste mount plan JSON...</option>
          {profiles.map((p) => (
            <option key={p.path} value={p.name}>
              {p.name}
            </option>
          ))}
        </select>

        {selectedProfile === CUSTOM_JSON_VALUE && customMountPlan && (
          <button
            onClick={() => setShowMountPlanInput(true)}
            disabled={!!session || loading}
            className="button small icon-btn"
            title="Edit custom mount plan"
          >
            <FileJson size={14} />
          </button>
        )}

        <div className="pane-controls">
          <button
            onClick={() => selectedProfile && selectedProfile !== CUSTOM_JSON_VALUE && onViewProfile(selectedProfile)}
            disabled={!selectedProfile || selectedProfile === CUSTOM_JSON_VALUE}
            className="button small"
            title="View profile"
          >
            View
          </button>
          {session && (
            <>
              <span className="status-badge running">Running</span>
              <button
                onClick={handleStopSession}
                disabled={loading}
                className="button danger small"
              >
                Stop
              </button>
              <button
                onClick={() => setShowInfo(true)}
                className="button small icon-btn"
                title="Session info"
              >
                <Info size={14} />
              </button>
            </>
          )}
          <button
            onClick={() => setShowEvents(!showEvents)}
            className={`button small ${showEvents ? 'active' : ''}`}
            title="Toggle events panel"
          >
            Events {events.length > 0 && `(${events.length})`}
          </button>
          <button onClick={onClose} className="button small close-btn" title="Close pane">
            X
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)} className="dismiss">
            Dismiss
          </button>
        </div>
      )}

      {/* Credential Warning Banner */}
      {credentialStatus && !credentialStatus.ready && !session && (
        <div className="warning-banner compact">
          <AlertTriangle size={14} />
          <span>
            Missing: {credentialStatus.credentials.filter((c) => !c.configured).map((c) => c.display_name).join(', ')}
          </span>
          {onOpenSettings && (
            <button onClick={onOpenSettings} className="configure-link">
              Configure
            </button>
          )}
        </div>
      )}

      {/* Main Content */}
      <div className="pane-content">
        {/* Messages */}
        <div className="messages-panel">
          <div className="messages">
            {messages.length === 0 ? (
              <div className="empty-state center">
                <p>{hasValidConfig ? 'Send a message to start' : 'Select a configuration to begin'}</p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <div className="message-header">
                    <span className="message-role">{msg.role}</span>
                    <span className="message-time">
                      {msg.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="message-content">
                    {msg.content.split('\n').map((line, j) => (
                      <p key={j}>{line || '\u00A0'}</p>
                    ))}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="input-area">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder={hasValidConfig ? 'Type a message to start...' : 'Select a configuration first'}
              disabled={!hasValidConfig || loading}
              rows={2}
              className="message-input"
            />
            <button
              onClick={handleSend}
              disabled={!hasValidConfig || !input.trim() || loading}
              className="button primary send-button"
            >
              {loading && !session ? 'Starting...' : 'Send'}
            </button>
          </div>
        </div>

        {/* Events Panel (collapsible) */}
        {showEvents && (
          <div className="events-panel">
            <div className="events-list">
              {events.length === 0 ? (
                <p className="empty-state">No events yet</p>
              ) : (
                events.map((e, i) => (
                  <div key={i} className="event-item">
                    <span className="event-type">{e.event}</span>
                    <pre className="event-data">
                      {JSON.stringify(e.data, null, 2)}
                    </pre>
                  </div>
                ))
              )}
              <div ref={eventsEndRef} />
            </div>
          </div>
        )}
      </div>

      {/* Session Info Modal */}
      {showInfo && session && (
        <SessionInfoModal
          sessionId={session.session_id}
          onClose={() => setShowInfo(false)}
        />
      )}

      {/* Mount Plan Input Modal */}
      {showMountPlanInput && (
        <MountPlanInputModal
          initialValue={customMountPlan ? JSON.stringify(customMountPlan, null, 2) : ''}
          onConfirm={(plan) => {
            setCustomMountPlan(plan);
            setShowMountPlanInput(false);
          }}
          onClose={() => {
            setShowMountPlanInput(false);
            // If no custom plan was set, revert selection
            if (!customMountPlan) {
              setSelectedProfile('');
            }
          }}
        />
      )}
    </div>
  );
}
