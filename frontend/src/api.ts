// API client for Amplifier Playground

import type { ProfileListItem, ProfileContent, ProfileDependencyGraph, SessionInfo, PromptResponse } from './types';

const API_BASE = '/api';

export async function listProfiles(): Promise<ProfileListItem[]> {
  const response = await fetch(`${API_BASE}/profiles`);
  if (!response.ok) {
    throw new Error(`Failed to list profiles: ${response.statusText}`);
  }
  return response.json();
}

export async function getProfileContent(profileName: string): Promise<ProfileContent> {
  const response = await fetch(`${API_BASE}/profiles/${encodeURIComponent(profileName)}/content`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to get profile: ${response.statusText}`);
  }
  return response.json();
}

export async function saveProfileContent(profileName: string, content: string): Promise<ProfileContent> {
  const response = await fetch(`${API_BASE}/profiles/${encodeURIComponent(profileName)}/content`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to save profile: ${response.statusText}`);
  }
  return response.json();
}

export async function getProfileDependencyGraph(profileName: string): Promise<ProfileDependencyGraph> {
  const response = await fetch(`${API_BASE}/profiles/${encodeURIComponent(profileName)}/graph`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to get dependency graph: ${response.statusText}`);
  }
  return response.json();
}

export async function createSession(profile: string): Promise<SessionInfo> {
  const response = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to create session: ${response.statusText}`);
  }
  return response.json();
}

export async function sendPrompt(sessionId: string, text: string): Promise<PromptResponse> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to send prompt: ${response.statusText}`);
  }
  return response.json();
}

export async function stopSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to stop session: ${response.statusText}`);
  }
}

export function subscribeToEvents(
  sessionId: string,
  onEvent: (event: string, data: Record<string, unknown>) => void,
  onError?: (error: Error) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/sessions/${sessionId}/events`);

  eventSource.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      onEvent(parsed.event, parsed.data);
    } catch (e) {
      console.error('Failed to parse event:', e);
    }
  };

  eventSource.onerror = () => {
    onError?.(new Error('Event stream error'));
    eventSource.close();
  };

  return () => eventSource.close();
}
