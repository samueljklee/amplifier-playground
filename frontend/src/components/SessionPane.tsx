import { useState, useEffect, useRef, useCallback } from 'react';
import { Info, FileJson, AlertTriangle, Blocks } from 'lucide-react';
import type { ProfileListItem, SessionInfo, Message, MountPlan } from '../types';
import { createSession, sendPrompt, stopSession, subscribeToEvents, getProfileCredentials, type ProfileCredentials } from '../api';
import { SessionInfoModal } from './SessionInfoModal';
import { MountPlanInputModal } from './MountPlanInputModal';

const CUSTOM_JSON_VALUE = '__custom_json__';
const BUILDER_VALUE = '__builder__';

interface SessionPaneProps {
  profiles: ProfileListItem[];
  onClose: () => void;
  onViewProfile: (profileName: string) => void;
  onOpenSettings?: () => void;
  onOpenBuilder?: () => void;
  builtMountPlan?: MountPlan | null;
}

export function SessionPane({ profiles, onClose, onViewProfile, onOpenSettings, onOpenBuilder, builtMountPlan }: SessionPaneProps) {
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
    if (!selectedProfile || selectedProfile === CUSTOM_JSON_VALUE || selectedProfile === BUILDER_VALUE) {
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
  const hasValidConfig = selectedProfile && selectedProfile !== CUSTOM_JSON_VALUE && selectedProfile !== BUILDER_VALUE
    ? true
    : (selectedProfile === BUILDER_VALUE ? builtMountPlan !== null : customMountPlan !== null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Track current SSE unsubscribe function
  const unsubscribeRef = useRef<(() => void) | null>(null);

  // Function to set up SSE subscription - called both from handleSend and useEffect
  const setupEventSubscription = useCallback((sessionId: string) => {
    // Clean up existing subscription if any
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
    }

    const unsubscribe = subscribeToEvents(
      sessionId,
      (event, data) => {
        // Debug: log all events to see their format
        console.log('[SessionPane] Event received:', event, typeof event);

        // Add to events panel
        setEvents((prev) => [...prev, { event, data }]);

        // Handle thinking and tool_call content from content_block:end
        // Note: We only use content_block:end because content_block:start and
        // thinking:delta events arrive in a race condition with React state updates.
        // The complete content is available in content_block:end.
        if (event === 'content_block:end') {
          const eventData = data as {
            block?: {
              type?: string;
              text?: string;
              thinking?: string;
              name?: string;
              id?: string;
              arguments?: Record<string, unknown>;
            };
            block_index?: number;
          };

          // Handle thinking blocks
          if (eventData.block?.type === 'thinking') {
            const thinkingText = eventData.block.thinking || eventData.block.text || '';
            if (thinkingText) {
              setMessages((prev) => [
                ...prev,
                {
                  role: 'thinking',
                  content: thinkingText,
                  timestamp: new Date(),
                },
              ]);
            }
          }

          // Handle tool_call blocks
          if (eventData.block?.type === 'tool_call') {
            const toolName = eventData.block.name || 'unknown';
            const toolId = eventData.block.id || '';
            const args = eventData.block.arguments || {};

            // Format the arguments for display (abbreviated for long content)
            let argsDisplay = JSON.stringify(args, null, 2);
            if (argsDisplay.length > 500) {
              argsDisplay = argsDisplay.substring(0, 500) + '\n... (truncated)';
            }

            setMessages((prev) => [
              ...prev,
              {
                role: 'tool',
                content: argsDisplay,
                toolName,
                toolId,
                timestamp: new Date(),
              },
            ]);
          }
        }

        // Handle tool:pre events to show tool calls starting
        if (event === 'tool:pre') {
          console.log('[SessionPane] tool:pre event received:', data);
          const eventData = data as {
            tool_name?: string;
            tool_input?: Record<string, unknown>;
          };

          const toolName = eventData.tool_name || 'unknown';
          const args = eventData.tool_input || {};

          // Format the arguments for display (abbreviated for long content)
          let argsDisplay = JSON.stringify(args, null, 2);
          if (argsDisplay.length > 500) {
            argsDisplay = argsDisplay.substring(0, 500) + '\n... (truncated)';
          }

          console.log('[SessionPane] Adding tool message:', toolName, argsDisplay.substring(0, 100));
          setMessages((prev) => [
            ...prev,
            {
              role: 'tool',
              content: argsDisplay,
              toolName,
              timestamp: new Date(),
            },
          ]);
        }

        // Handle tool:post events to show results
        if (event === 'tool:post') {
          const eventData = data as {
            tool_name?: string;
            result?: {
              success?: boolean;
              output?: unknown;
              error?: { message?: string };
            };
          };

          const toolName = eventData.tool_name || 'unknown';
          const result = eventData.result;
          const success = result?.success ?? true;

          let resultContent: string;
          if (result?.error?.message) {
            resultContent = `Error: ${result.error.message}`;
          } else if (result?.output) {
            resultContent = typeof result.output === 'string'
              ? result.output
              : JSON.stringify(result.output, null, 2);
            // Truncate long outputs
            if (resultContent.length > 1000) {
              resultContent = resultContent.substring(0, 1000) + '\n... (truncated)';
            }
          } else {
            resultContent = success ? 'Completed successfully' : 'Failed';
          }

          setMessages((prev) => [
            ...prev,
            {
              role: 'tool-result',
              content: resultContent,
              toolName,
              toolSuccess: success,
              timestamp: new Date(),
            },
          ]);
        }
      },
      (err) => {
        console.error('Event stream error:', err);
      }
    );

    unsubscribeRef.current = unsubscribe;
    return unsubscribe;
  }, []);

  // Subscribe to session events on mount/session change (for reconnection scenarios)
  useEffect(() => {
    if (!session) return;

    // Only set up if not already subscribed (handleSend sets it up for new sessions)
    if (!unsubscribeRef.current) {
      setupEventSubscription(session.session_id);
    }

    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
    };
  }, [session, setupEventSubscription]);

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

        // Create session with profile, custom mount plan, or built mount plan
        const isCustomJson = selectedProfile === CUSTOM_JSON_VALUE && customMountPlan;
        const isBuilder = selectedProfile === BUILDER_VALUE && builtMountPlan;

        if (isBuilder) {
          currentSession = await createSession({ mountPlan: builtMountPlan });
        } else if (isCustomJson) {
          currentSession = await createSession({ mountPlan: customMountPlan });
        } else {
          currentSession = await createSession({ profile: selectedProfile });
        }

        // Set up SSE subscription IMMEDIATELY before sending prompt
        // This ensures we capture thinking events from the first message
        setupEventSubscription(currentSession.session_id);

        setSession(currentSession);
        setMessages([
          {
            role: 'system',
            content: isBuilder
              ? 'Session started with built mount plan'
              : isCustomJson
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
      // Note: Thinking blocks are streamed in real-time via SSE events above,
      // so we only add the assistant's text response from the final response.
      const response = await sendPrompt(currentSession.session_id, userMessage);

      // Add the assistant's text response (thinking already streamed via SSE)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.response,
          timestamp: new Date(),
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to send message');
    } finally {
      setLoading(false);
    }
  }, [session, input, selectedProfile, customMountPlan, builtMountPlan, hasValidConfig, setupEventSubscription]);

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
            } else if (value === BUILDER_VALUE && onOpenBuilder) {
              onOpenBuilder();
            } else {
              setCustomMountPlan(null);
            }
          }}
          disabled={!!session || loading}
          className="profile-select-inline"
        >
          <option value="">Select configuration...</option>
          <option value={BUILDER_VALUE}>Build custom mount plan...</option>
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

        {selectedProfile === BUILDER_VALUE && builtMountPlan && onOpenBuilder && (
          <button
            onClick={onOpenBuilder}
            disabled={!!session || loading}
            className="button small icon-btn"
            title="Edit mount plan in builder"
          >
            <Blocks size={14} />
          </button>
        )}

        <div className="pane-controls">
          <button
            onClick={() => selectedProfile && selectedProfile !== CUSTOM_JSON_VALUE && selectedProfile !== BUILDER_VALUE && onViewProfile(selectedProfile)}
            disabled={!selectedProfile || selectedProfile === CUSTOM_JSON_VALUE || selectedProfile === BUILDER_VALUE}
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
                <div key={i} className={`message ${msg.role}${msg.toolSuccess === false ? ' error' : ''}`}>
                  <div className="message-header">
                    <span className="message-role">
                      {msg.role === 'tool' && msg.toolName
                        ? `tool: ${msg.toolName}`
                        : msg.role === 'tool-result' && msg.toolName
                        ? `result: ${msg.toolName}`
                        : msg.role}
                    </span>
                    {msg.role === 'tool-result' && (
                      <span className={`tool-status ${msg.toolSuccess ? 'success' : 'error'}`}>
                        {msg.toolSuccess ? 'success' : 'failed'}
                      </span>
                    )}
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
