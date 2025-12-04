// API Types for Amplifier Playground

export interface ProfileListItem {
  name: string;
  collection: string | null;
  profile: string;
  path: string;
}

export interface ProfileInfo {
  name: string;
  description: string | null;
  extends: string[] | null;
  agents_count: number;
  context_count: number;
  has_system_prompt: boolean;
}

export interface SessionInfo {
  session_id: string;
  is_running: boolean;
  profile: string | null;
  config_id: string | null;
}

export interface SessionDetailInfo {
  session_id: string;
  is_running: boolean;
  profile: string | null;
  config_id: string | null;
  parent_session_id: string | null;
  mount_plan: Record<string, unknown> | null;
  approval_mode: string | null;
  created_at: string | null;
}

export interface PromptResponse {
  response: string;
  session_id: string;
}

export interface SessionEvent {
  event: string;
  data: Record<string, unknown>;
}

export interface CredentialStatus {
  configured: boolean;
  source: 'env' | 'file' | null;
  masked_value: string | null;
}

export interface CredentialInfo {
  key: string;
  env_var: string;
  display_name: string;
  configured: boolean;
  source: 'env' | 'file' | null;
  masked_value: string | null;
}

export interface CustomCredentialInfo {
  env_var: string;
  masked_value: string;
  is_custom: boolean;
}

export interface CredentialsStatus {
  credentials: CredentialInfo[];
  custom_credentials: CustomCredentialInfo[];
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface ProfileContent {
  name: string;
  path: string;
  content: string;
}

export interface DependencyFile {
  path: string;
  name: string;
  content: string;
  file_type: 'profile' | 'context' | 'agent';
  relationship: 'root' | 'extends' | 'mentions' | 'agents';
  referenced_by: string[];  // Paths of files that reference this one
}

export interface ProfileDependencyGraph {
  profile_name: string;
  files: DependencyFile[];
  mount_plan: MountPlan | null;
}

// Mount Plan types
export interface MountPlan {
  session?: {
    orchestrator?: string;
    context?: string;
    [key: string]: unknown;
  };
  providers?: ModuleEntry[];
  tools?: ModuleEntry[];
  hooks?: ModuleEntry[];
  agents?: Record<string, AgentConfig>;
  [key: string]: unknown;
}

export interface ModuleEntry {
  module: string;
  config?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface AgentConfig {
  description?: string;
  session?: Record<string, unknown>;
  tools?: string[];
  [key: string]: unknown;
}
