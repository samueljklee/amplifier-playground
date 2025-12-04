// API client for Amplifier Playground

import type { ProfileListItem, ProfileContent, ProfileDependencyGraph, SessionInfo, SessionDetailInfo, PromptResponse, CredentialsStatus } from './types';

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

export interface CredentialRequirement {
  provider: string;
  credential_key: string;
  env_var: string;
  configured: boolean;
  display_name: string;
}

export interface ProfileCredentials {
  profile: string;
  providers: string[];
  credentials: CredentialRequirement[];
  ready: boolean;
}

export async function getProfileCredentials(profileName: string): Promise<ProfileCredentials> {
  const response = await fetch(`${API_BASE}/profiles/${encodeURIComponent(profileName)}/credentials`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to check credentials: ${response.statusText}`);
  }
  return response.json();
}

export interface CreateSessionOptions {
  profile?: string;
  mountPlan?: Record<string, unknown>;
}

export async function createSession(options: CreateSessionOptions): Promise<SessionInfo> {
  const body: Record<string, unknown> = {};
  if (options.profile) {
    body.profile = options.profile;
  } else if (options.mountPlan) {
    body.mount_plan = options.mountPlan;
  }

  const response = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
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

export async function getSessionDetails(sessionId: string): Promise<SessionDetailInfo> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/details`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to get session details: ${response.statusText}`);
  }
  return response.json();
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

// Settings API

export async function getCredentialsStatus(): Promise<CredentialsStatus> {
  const response = await fetch(`${API_BASE}/settings/credentials`);
  if (!response.ok) {
    throw new Error(`Failed to get credentials status: ${response.statusText}`);
  }
  return response.json();
}

export async function setCredential(credentialKey: string, value: string): Promise<void> {
  const response = await fetch(`${API_BASE}/settings/credentials/${encodeURIComponent(credentialKey)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to save credential: ${response.statusText}`);
  }
}

export async function deleteCredential(credentialKey: string): Promise<void> {
  const response = await fetch(`${API_BASE}/settings/credentials/${encodeURIComponent(credentialKey)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to delete credential: ${response.statusText}`);
  }
}

// Custom credentials
export async function addCustomCredential(envVar: string, value: string): Promise<void> {
  const response = await fetch(`${API_BASE}/settings/credentials/custom`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ env_var: envVar, value }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to add custom credential: ${response.statusText}`);
  }
}

export async function deleteCustomCredential(envVar: string): Promise<void> {
  const response = await fetch(`${API_BASE}/settings/credentials/custom/${encodeURIComponent(envVar)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to delete custom credential: ${response.statusText}`);
  }
}
