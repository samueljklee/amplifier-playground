import { useState, useEffect, useRef, useCallback } from 'react';
import type { ProfileListItem, SessionInfo, Message } from '../types';
import { createSession, sendPrompt, stopSession, subscribeToEvents } from '../api';

interface SessionPaneProps {
  profiles: ProfileListItem[];
  onClose: () => void;
  onViewProfile: (profileName: string) => void;
}

export function SessionPane({ profiles, onClose, onViewProfile }: SessionPaneProps) {
  const [selectedProfile, setSelectedProfile] = useState<string>('');
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<Array<{ event: string; data: unknown }>>([]);
  const [showEvents, setShowEvents] = useState(false);

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

  const handleStartSession = useCallback(async () => {
    if (!selectedProfile) return;

    setLoading(true);
    setError(null);
    setMessages([]);
    setEvents([]);

    try {
      const newSession = await createSession(selectedProfile);
      setSession(newSession);
      setMessages([
        {
          role: 'system',
          content: `Session started with profile: ${selectedProfile}`,
          timestamp: new Date(),
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start session');
    } finally {
      setLoading(false);
    }
  }, [selectedProfile]);

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
    if (!session || !input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage, timestamp: new Date() },
    ]);
    setLoading(true);

    try {
      const response = await sendPrompt(session.session_id, userMessage);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.response, timestamp: new Date() },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to send message');
    } finally {
      setLoading(false);
    }
  }, [session, input]);

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
          onChange={(e) => setSelectedProfile(e.target.value)}
          disabled={!!session || loading}
          className="profile-select-inline"
        >
          <option value="">Select profile...</option>
          {profiles.map((p) => (
            <option key={p.path} value={p.name}>
              {p.name}
            </option>
          ))}
        </select>

        <div className="pane-controls">
          <button
            onClick={() => selectedProfile && onViewProfile(selectedProfile)}
            disabled={!selectedProfile}
            className="button small"
            title="View profile"
          >
            View
          </button>
          {!session ? (
            <button
              onClick={handleStartSession}
              disabled={!selectedProfile || loading}
              className="button primary small"
            >
              {loading ? 'Starting...' : 'Start'}
            </button>
          ) : (
            <>
              <span className="status-badge running">Running</span>
              <button
                onClick={handleStopSession}
                disabled={loading}
                className="button danger small"
              >
                Stop
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

      {/* Main Content */}
      <div className="pane-content">
        {/* Messages */}
        <div className="messages-panel">
          <div className="messages">
            {messages.length === 0 ? (
              <div className="empty-state center">
                <p>Select a profile and start a session</p>
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
              placeholder={session ? 'Type a message...' : 'Start a session first'}
              disabled={!session || loading}
              rows={2}
              className="message-input"
            />
            <button
              onClick={handleSend}
              disabled={!session || !input.trim() || loading}
              className="button primary send-button"
            >
              Send
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
    </div>
  );
}
