import { useState, useEffect, useCallback, useMemo, type DragEvent } from 'react';
import {
  X,
  Search,
  Zap,
  Wrench,
  GitBranch,
  Play,
  Trash2,
  Settings,
  ChevronDown,
  ChevronRight,
  Cpu,
  Database,
  Bot,
  Plus,
  FileText,
  Code,
  Blocks,
} from 'lucide-react';
import type { ModuleInfo, MountPlan, ModuleEntry, AgentConfig } from '../types';
import { listModules, listProfiles, getProfileDependencyGraph, listCollections, getCollectionInfo } from '../api';
import type { ProfileListItem } from '../types';

// Profile resource item for display in palette
interface ProfileResource {
  name: string;
  path: string;
  content: string;
  file_type: 'agent' | 'context';
}
import './MountPlanBuilder.css';

interface MountPlanBuilderProps {
  onClose: () => void;
  onLaunch: (mountPlan: MountPlan) => void;
  initialMountPlan?: MountPlan | null;
}

interface BuilderModule extends ModuleEntry {
  id: string;
}

interface BuilderAgent {
  id: string;
  name: string;
  description: string;
  instruction?: string;
  tools: string[];
}

interface BuilderState {
  providers: BuilderModule[];
  tools: BuilderModule[];
  hooks: BuilderModule[];
  agents: BuilderAgent[];
}

interface SessionSettings {
  orchestrator: string;
  context: string;
  orchestratorConfig?: Record<string, unknown>;
  contextConfig?: Record<string, unknown>;
}

const CATEGORY_ICONS: Record<string, typeof Zap> = {
  provider: Zap,
  tool: Wrench,
  hook: GitBranch,
  orchestrator: Cpu,
  context: Database,
  agent: Bot,
  'profile-agent': Bot,
  'profile-context': FileText,
};

const CATEGORY_COLORS: Record<string, string> = {
  provider: '#a855f7',
  tool: '#3b82f6',
  hook: '#f59e0b',
  orchestrator: '#10b981',
  context: '#06b6d4',
  agent: '#ec4899',
  'profile-agent': '#ec4899',
  'profile-context': '#8b5cf6',
};

// Known orchestrators and contexts with their source URLs
const KNOWN_ORCHESTRATORS = [
  {
    id: 'loop-basic',
    name: 'Basic Loop',
    description: 'Simple synchronous execution loop',
    source: 'git+https://github.com/microsoft/amplifier-module-loop-basic@main',
  },
  {
    id: 'loop-streaming',
    name: 'Streaming Loop',
    description: 'Streaming execution with real-time output',
    source: 'git+https://github.com/microsoft/amplifier-module-loop-streaming@main',
  },
];

const KNOWN_CONTEXTS = [
  {
    id: 'context-simple',
    name: 'Simple Context',
    description: 'In-memory context management',
    source: 'git+https://github.com/microsoft/amplifier-module-context-simple@main',
  },
  {
    id: 'context-persistent',
    name: 'Persistent Context',
    description: 'File-based persistent context',
    source: 'git+https://github.com/microsoft/amplifier-module-context-persistent@main',
  },
];

export function MountPlanBuilder({ onClose, onLaunch, initialMountPlan }: MountPlanBuilderProps) {
  const [modules, setModules] = useState<ModuleInfo[]>([]);
  const [profiles, setProfiles] = useState<ProfileListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedCategory, setExpandedCategory] = useState<string | null>('provider');
  const [dragOverZone, setDragOverZone] = useState<string | null>(null);
  const [dragOverProfileResources, setDragOverProfileResources] = useState(false);
  const [dragOverAgents, setDragOverAgents] = useState(false);
  const [showProfileImport, setShowProfileImport] = useState(false);

  // Session settings
  const [sessionSettings, setSessionSettings] = useState<SessionSettings>({
    orchestrator: 'loop-streaming',
    context: 'context-simple',
    orchestratorConfig: undefined,
    contextConfig: undefined,
  });

  // Builder state
  const [builderState, setBuilderState] = useState<BuilderState>({
    providers: [],
    tools: [],
    hooks: [],
    agents: [],
  });

  // Selected module for config editing
  const [selectedModule, setSelectedModule] = useState<{
    zone: keyof Omit<BuilderState, 'agents'>;
    index: number;
  } | null>(null);
  const [configInput, setConfigInput] = useState('');

  // Agent editing
  const [editingAgent, setEditingAgent] = useState<{ index: number } | null>(null);
  const [agentForm, setAgentForm] = useState({ name: '', description: '', tools: '' });

  // View mode toggle (builder vs JSON)
  const [viewMode, setViewMode] = useState<'builder' | 'json'>('builder');

  // JSON editing state
  const [jsonEditText, setJsonEditText] = useState<string>('');
  const [jsonEditError, setJsonEditError] = useState<string | null>(null);

  // Available resources from collections (read-only source for palette)
  const [availableResources, setAvailableResources] = useState<ProfileResource[]>([]);
  // Dropped resources on canvas (mutable state for mount plan)
  const [droppedResources, setDroppedResources] = useState<ProfileResource[]>([]);
  const [_selectedProfileName, setSelectedProfileName] = useState<string | null>(null);

  // Initialize from initial mount plan if provided
  useEffect(() => {
    if (!initialMountPlan) return;

    // Parse session settings
    if (initialMountPlan.session) {
      const orch = initialMountPlan.session.orchestrator;
      const ctx = initialMountPlan.session.context;
      setSessionSettings({
        orchestrator: typeof orch === 'string' ? orch : orch?.module || 'loop-streaming',
        context: typeof ctx === 'string' ? ctx : ctx?.module || 'context-simple',
        orchestratorConfig: (initialMountPlan as any).orchestrator?.config,
        contextConfig: (initialMountPlan as any).context?.config,
      });
    }

    // Parse providers, tools, hooks
    const newState: BuilderState = {
      providers: (initialMountPlan.providers || []).map((p) => ({
        id: crypto.randomUUID(),
        module: p.module,
        source: p.source,
        config: p.config,
      })),
      tools: (initialMountPlan.tools || []).map((t) => ({
        id: crypto.randomUUID(),
        module: t.module,
        source: t.source,
        config: t.config,
      })),
      hooks: (initialMountPlan.hooks || []).map((h) => ({
        id: crypto.randomUUID(),
        module: h.module,
        source: h.source,
        config: h.config,
      })),
      agents: initialMountPlan.agents
        ? Object.entries(initialMountPlan.agents).map(([name, config]) => ({
            id: crypto.randomUUID(),
            name,
            description: config.description || '',
            tools: config.tools || [],
          }))
        : [],
    };

    setBuilderState(newState);
  }, [initialMountPlan]);

  // Load modules and profiles on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [allModules, allProfiles, allCollections] = await Promise.all([
        listModules(),
        listProfiles(),
        listCollections(),
      ]);
      setModules(allModules);
      setProfiles(allProfiles);

      // Load profile resources (agents and context files) from ALL collections
      // This populates the palette with all available options
      if (allCollections.length > 0) {
        const allResources: ProfileResource[] = [];
        const seenNames = new Set<string>();

        // Fetch collection info from all collections in parallel
        const collectionPromises = allCollections.map((collectionName) =>
          getCollectionInfo(collectionName).catch((e) => {
            console.warn(`Failed to load collection ${collectionName}:`, e);
            return null;
          })
        );
        const collections = await Promise.all(collectionPromises);

        // Extract and deduplicate resources from all collections
        for (const collection of collections) {
          if (!collection) continue;

          // Add agents from this collection
          for (const agentPath of collection.resources.agents) {
            // Extract agent name from absolute path (e.g., '/Users/.../agents/bug-hunter.md' -> 'bug-hunter')
            const fileName = agentPath.split('/').pop() || agentPath;
            const agentName = fileName.replace(/\.md$/, '');
            if (!seenNames.has(`agent:${agentName}`)) {
              seenNames.add(`agent:${agentName}`);
              allResources.push({
                name: agentName,
                path: agentPath, // API returns absolute path
                content: '', // Content loaded on demand when dragged
                file_type: 'agent',
              });
            }
          }

          // Add context files from this collection
          for (const contextPath of collection.resources.context) {
            // Extract context name from absolute path (e.g., '/Users/.../context/context-simple.md' -> 'context-simple')
            const fileName = contextPath.split('/').pop() || contextPath;
            const contextName = fileName.replace(/\.md$/, '');
            if (!seenNames.has(`context:${contextName}`)) {
              seenNames.add(`context:${contextName}`);
              allResources.push({
                name: contextName,
                path: contextPath, // API returns absolute path
                content: '', // Content loaded on demand when dragged
                file_type: 'context',
              });
            }
          }
        }

        setAvailableResources(allResources);
      }

      // Auto-load the first profile's configuration into the canvas
      // if no initial mount plan was provided
      if (!initialMountPlan && allProfiles.length > 0) {
        const firstGraph = await getProfileDependencyGraph(allProfiles[0].name).catch(() => null);
        if (firstGraph?.mount_plan) {
          const plan = firstGraph.mount_plan;
          setSelectedProfileName(allProfiles[0].name);

          // Import session settings
          if (plan.session) {
            setSessionSettings({
              orchestrator: (plan.session.orchestrator as string) || 'loop-streaming',
              context: (plan.session.context as string) || 'context-simple',
            });
          }

          // Import providers
          if (plan.providers) {
            const newProviders: BuilderModule[] = plan.providers.map((p) => ({
              id: crypto.randomUUID(),
              module: p.module,
              source: p.source,
              config: p.config,
            }));
            setBuilderState((prev) => ({
              ...prev,
              providers: newProviders,
            }));
          }

          // Import tools
          if (plan.tools) {
            const newTools: BuilderModule[] = plan.tools.map((t) => ({
              id: crypto.randomUUID(),
              module: t.module,
              source: t.source,
              config: t.config,
            }));
            setBuilderState((prev) => ({
              ...prev,
              tools: newTools,
            }));
          }

          // Import hooks
          if (plan.hooks) {
            const newHooks: BuilderModule[] = plan.hooks.map((h) => ({
              id: crypto.randomUUID(),
              module: h.module,
              source: h.source,
              config: h.config,
            }));
            setBuilderState((prev) => ({
              ...prev,
              hooks: newHooks,
            }));
          }

          // Import agents
          if (plan.agents) {
            const newAgents: BuilderAgent[] = Object.entries(plan.agents as Record<string, AgentConfig>).map(
              ([name, config]) => ({
                id: crypto.randomUUID(),
                name,
                description: config.description || '',
                tools: config.tools || [],
              })
            );
            setBuilderState((prev) => ({
              ...prev,
              agents: newAgents,
            }));
          }
        }
      }
    } catch (e) {
      console.error('Failed to load data:', e);
    } finally {
      setLoading(false);
    }
  };

  // Filter modules by search and category
  const filteredModules = modules.filter((m) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      m.id.toLowerCase().includes(searchLower) ||
      m.name.toLowerCase().includes(searchLower) ||
      (m.description && m.description.toLowerCase().includes(searchLower))
    );
  });

  const modulesByCategory = {
    provider: filteredModules.filter((m) => m.category === 'provider'),
    tool: filteredModules.filter((m) => m.category === 'tool'),
    hook: filteredModules.filter((m) => m.category === 'hook'),
  };

  // Map zones to their expected module categories
  const zoneToCategoryMap: Record<string, string> = {
    providers: 'provider',
    tools: 'tool',
    hooks: 'hook',
  };

  // Drag handlers
  const handleDragStart = (e: DragEvent, module: ModuleInfo) => {
    e.dataTransfer.setData('application/json', JSON.stringify(module));
    e.dataTransfer.effectAllowed = 'copy';
  };

  // Drag handler for profile resources (agents and context files)
  const handleProfileResourceDragStart = (e: DragEvent, resource: ProfileResource) => {
    // Create a ModuleInfo-like object for the drop handler
    const moduleData = {
      id: resource.name,
      name: resource.name,
      category: resource.file_type === 'agent' ? 'profile-agent' : 'profile-context',
      description: resource.path,
      content: resource.content,
      path: resource.path,
    };
    e.dataTransfer.setData('application/json', JSON.stringify(moduleData));
    e.dataTransfer.effectAllowed = 'copy';
  };

  // Check if a module category is valid for a zone
  const isValidDropTarget = (moduleCategory: string, zone: string): boolean => {
    const expectedCategory = zoneToCategoryMap[zone];
    return expectedCategory === moduleCategory;
  };

  const handleDragOver = (e: DragEvent, zone: string) => {
    e.preventDefault();
    // Try to get category from drag data to validate drop target
    // Note: dataTransfer.getData() may not work in dragover due to browser security
    // So we allow the visual feedback but will validate in handleDrop
    e.dataTransfer.dropEffect = 'copy';
    setDragOverZone(zone);
  };

  const handleDragLeave = () => {
    setDragOverZone(null);
  };

  const handleDrop = (e: DragEvent, zone: keyof Omit<BuilderState, 'agents'>) => {
    e.preventDefault();
    setDragOverZone(null);

    try {
      const moduleData = JSON.parse(e.dataTransfer.getData('application/json')) as ModuleInfo;

      // Validate category matches zone
      if (!isValidDropTarget(moduleData.category, zone)) {
        console.warn(`Cannot drop ${moduleData.category} module into ${zone} zone`);
        return;
      }

      // Check if module is already in the zone
      const existing = builderState[zone].find((m) => m.module === moduleData.id);
      if (existing) return;

      // Add module to the zone (include source for module resolution)
      const newModule: BuilderModule = {
        id: crypto.randomUUID(),
        module: moduleData.id,
        source: moduleData.source || undefined,
      };

      setBuilderState((prev) => ({
        ...prev,
        [zone]: [...prev[zone], newModule],
      }));
    } catch (err) {
      console.error('Failed to parse dropped data:', err);
    }
  };

  // Handle profile resource drop on canvas
  const handleProfileResourceDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOverProfileResources(false);
    try {
      const moduleData = JSON.parse(e.dataTransfer.getData('application/json'));
      // Only accept profile-agent and profile-context categories
      if (moduleData.category !== 'profile-agent' && moduleData.category !== 'profile-context') {
        return;
      }

      // Check if resource already exists in dropped resources
      const exists = droppedResources.some(
        (r) => r.path === moduleData.path && r.file_type === (moduleData.category === 'profile-agent' ? 'agent' : 'context')
      );
      if (exists) return;

      // Add to dropped resources (not availableResources - that's the source)
      const newResource: ProfileResource = {
        name: moduleData.name,
        path: moduleData.path,
        content: moduleData.content || '',
        file_type: moduleData.category === 'profile-agent' ? 'agent' : 'context',
      };
      setDroppedResources((prev) => [...prev, newResource]);
    } catch (err) {
      console.error('Failed to parse dropped profile resource:', err);
    }
  };

  // Handle profile agent drop on agents section
  const handleAgentDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOverAgents(false);
    try {
      const moduleData = JSON.parse(e.dataTransfer.getData('application/json'));
      // Only accept profile-agent category
      if (moduleData.category !== 'profile-agent') {
        return;
      }

      // Check if agent with this name already exists
      const exists = builderState.agents.some((a) => a.name === moduleData.name);
      if (exists) return;

      // Create a new agent from the profile agent
      const newAgent: BuilderAgent = {
        id: crypto.randomUUID(),
        name: moduleData.name,
        description: moduleData.description || `Agent from ${moduleData.path}`,
        instruction: moduleData.path,
        tools: [],
      };
      setBuilderState((prev) => ({
        ...prev,
        agents: [...prev.agents, newAgent],
      }));
    } catch (err) {
      console.error('Failed to parse dropped agent:', err);
    }
  };

  // Apply JSON changes to builder state
  const applyJsonChanges = () => {
    try {
      const parsed = JSON.parse(jsonEditText);
      setJsonEditError(null);

      // Update session settings
      if (parsed.session) {
        const orch = parsed.session.orchestrator;
        const ctx = parsed.session.context;
        setSessionSettings({
          orchestrator: typeof orch === 'string' ? orch : orch?.module || 'loop-streaming',
          context: typeof ctx === 'string' ? ctx : ctx?.module || 'context-simple',
        });
      }

      // Update builder state (providers, tools, hooks, agents)
      const newBuilderState: BuilderState = {
        providers: [],
        tools: [],
        hooks: [],
        agents: [],
      };

      // Parse providers
      if (Array.isArray(parsed.providers)) {
        newBuilderState.providers = parsed.providers.map((p: { module?: string; config?: Record<string, unknown>; source?: string }, i: number) => ({
          id: crypto.randomUUID(),
          name: p.module || `provider-${i}`,
          description: '',
          config: p.config || {},
          source: p.source,
        }));
      }

      // Parse tools
      if (Array.isArray(parsed.tools)) {
        newBuilderState.tools = parsed.tools.map((t: { module?: string; config?: Record<string, unknown>; source?: string }, i: number) => ({
          id: crypto.randomUUID(),
          name: t.module || `tool-${i}`,
          description: '',
          config: t.config || {},
          source: t.source,
        }));
      }

      // Parse hooks
      if (Array.isArray(parsed.hooks)) {
        newBuilderState.hooks = parsed.hooks.map((h: { module?: string; config?: Record<string, unknown>; source?: string }, i: number) => ({
          id: crypto.randomUUID(),
          name: h.module || `hook-${i}`,
          description: '',
          config: h.config || {},
          source: h.source,
        }));
      }

      // Parse agents
      if (parsed.agents && typeof parsed.agents === 'object' && !Array.isArray(parsed.agents)) {
        newBuilderState.agents = Object.entries(parsed.agents).map(([name, agentConfig]) => ({
          id: crypto.randomUUID(),
          name,
          description: (agentConfig as { description?: string }).description || '',
          tools: (agentConfig as { tools?: string[] }).tools || [],
        }));
      }

      setBuilderState(newBuilderState);
    } catch (err) {
      setJsonEditError(err instanceof Error ? err.message : 'Invalid JSON');
    }
  };

  // Remove a profile resource from the drop zone (not the palette)
  const removeProfileResource = (index: number) => {
    setDroppedResources((prev) => prev.filter((_, i) => i !== index));
  };

  // Remove module from zone
  const removeModule = useCallback((zone: keyof Omit<BuilderState, 'agents'>, index: number) => {
    setBuilderState((prev) => ({
      ...prev,
      [zone]: prev[zone].filter((_, i) => i !== index),
    }));
    setSelectedModule(null);
  }, []);

  // Update module config
  const updateModuleConfig = useCallback(
    (zone: keyof Omit<BuilderState, 'agents'>, index: number, config: Record<string, unknown>) => {
      setBuilderState((prev) => ({
        ...prev,
        [zone]: prev[zone].map((m, i) => (i === index ? { ...m, config } : m)),
      }));
    },
    []
  );

  // Handle config save
  const handleSaveConfig = () => {
    if (!selectedModule) return;
    try {
      const config = configInput.trim() ? JSON.parse(configInput) : undefined;
      updateModuleConfig(selectedModule.zone, selectedModule.index, config);
      setSelectedModule(null);
      setConfigInput('');
    } catch {
      alert('Invalid JSON configuration');
    }
  };

  // Select module for editing
  const selectModuleForEdit = (zone: keyof Omit<BuilderState, 'agents'>, index: number) => {
    const module = builderState[zone][index];
    setSelectedModule({ zone, index });
    setConfigInput(module.config ? JSON.stringify(module.config, null, 2) : '');
  };

  // Agent management
  const addAgent = () => {
    if (!agentForm.name.trim()) {
      alert('Agent name is required');
      return;
    }

    const newAgent: BuilderAgent = {
      id: crypto.randomUUID(),
      name: agentForm.name.trim(),
      description: agentForm.description.trim(),
      tools: agentForm.tools
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    };

    setBuilderState((prev) => ({
      ...prev,
      agents: [...prev.agents, newAgent],
    }));

    setAgentForm({ name: '', description: '', tools: '' });
    setEditingAgent(null);
  };

  const updateAgent = () => {
    if (editingAgent === null) return;
    if (!agentForm.name.trim()) {
      alert('Agent name is required');
      return;
    }

    setBuilderState((prev) => ({
      ...prev,
      agents: prev.agents.map((agent, i) =>
        i === editingAgent.index
          ? {
              ...agent,
              name: agentForm.name.trim(),
              description: agentForm.description.trim(),
              tools: agentForm.tools
                .split(',')
                .map((t) => t.trim())
                .filter(Boolean),
            }
          : agent
      ),
    }));

    setAgentForm({ name: '', description: '', tools: '' });
    setEditingAgent(null);
  };

  const removeAgent = (index: number) => {
    setBuilderState((prev) => ({
      ...prev,
      agents: prev.agents.filter((_, i) => i !== index),
    }));
  };

  const editAgent = (index: number) => {
    const agent = builderState.agents[index];
    setAgentForm({
      name: agent.name,
      description: agent.description,
      tools: agent.tools.join(', '),
    });
    setEditingAgent({ index });
  };

  // Import from profile - loads the profile's configuration into the builder canvas
  // Note: Profile resources (agents, contexts) are already loaded from ALL profiles in loadData()
  // This function only populates the canvas state, not the palette
  const importFromProfile = async (profileName: string) => {
    try {
      const graph = await getProfileDependencyGraph(profileName);
      setSelectedProfileName(profileName);

      if (graph.mount_plan) {
        const plan = graph.mount_plan;

        // Import session settings
        if (plan.session) {
          setSessionSettings({
            orchestrator: (plan.session.orchestrator as string) || 'loop-streaming',
            context: (plan.session.context as string) || 'context-simple',
          });
        }

        // Import providers
        if (plan.providers) {
          const newProviders: BuilderModule[] = plan.providers.map((p) => ({
            id: crypto.randomUUID(),
            module: p.module,
            source: p.source,
            config: p.config,
          }));
          setBuilderState((prev) => ({
            ...prev,
            providers: [...prev.providers, ...newProviders],
          }));
        }

        // Import tools
        if (plan.tools) {
          const newTools: BuilderModule[] = plan.tools.map((t) => ({
            id: crypto.randomUUID(),
            module: t.module,
            source: t.source,
            config: t.config,
          }));
          setBuilderState((prev) => ({
            ...prev,
            tools: [...prev.tools, ...newTools],
          }));
        }

        // Import hooks
        if (plan.hooks) {
          const newHooks: BuilderModule[] = plan.hooks.map((h) => ({
            id: crypto.randomUUID(),
            module: h.module,
            source: h.source,
            config: h.config,
          }));
          setBuilderState((prev) => ({
            ...prev,
            hooks: [...prev.hooks, ...newHooks],
          }));
        }

        // Import agents
        if (plan.agents) {
          const newAgents: BuilderAgent[] = Object.entries(plan.agents as Record<string, AgentConfig>).map(
            ([name, config]) => ({
              id: crypto.randomUUID(),
              name,
              description: config.description || '',
              tools: config.tools || [],
            })
          );
          setBuilderState((prev) => ({
            ...prev,
            agents: [...prev.agents, ...newAgents],
          }));
        }
      }

      setShowProfileImport(false);
    } catch (e) {
      console.error('Failed to import profile:', e);
      alert(`Failed to import profile: ${e}`);
    }
  };

  // Build mount plan from state
  const buildMountPlan = (): MountPlan => {
    // Find the selected orchestrator and context with their sources
    const selectedOrchestrator = KNOWN_ORCHESTRATORS.find(o => o.id === sessionSettings.orchestrator);
    const selectedContext = KNOWN_CONTEXTS.find(c => c.id === sessionSettings.context);

    const plan: MountPlan = {
      session: {
        orchestrator: {
          module: sessionSettings.orchestrator,
          source: selectedOrchestrator?.source,
        },
        context: {
          module: sessionSettings.context,
          source: selectedContext?.source,
        },
      },
    };

    // Add orchestrator config if provided
    if (sessionSettings.orchestratorConfig && Object.keys(sessionSettings.orchestratorConfig).length > 0) {
      (plan as any).orchestrator = {
        config: sessionSettings.orchestratorConfig,
      };
    }

    // Add context config if provided
    if (sessionSettings.contextConfig && Object.keys(sessionSettings.contextConfig).length > 0) {
      (plan as any).context = {
        config: sessionSettings.contextConfig,
      };
    }

    if (builderState.providers.length > 0) {
      plan.providers = builderState.providers.map(({ module, source, config }) => ({
        module,
        ...(source && { source }),
        ...(config && { config }),
      }));
    }

    if (builderState.tools.length > 0) {
      plan.tools = builderState.tools.map(({ module, source, config }) => ({
        module,
        ...(source && { source }),
        ...(config && { config }),
      }));
    }

    if (builderState.hooks.length > 0) {
      plan.hooks = builderState.hooks.map(({ module, source, config }) => ({
        module,
        ...(source && { source }),
        ...(config && { config }),
      }));
    }

    if (builderState.agents.length > 0) {
      plan.agents = {};
      for (const agent of builderState.agents) {
        plan.agents[agent.name] = {
          instruction: agent.instruction || undefined,
          description: agent.description || undefined,
          tools: agent.tools.length > 0 ? agent.tools : undefined,
        };
      }
    }

    // Add dropped agents from profile resources
    const droppedAgents = droppedResources.filter((r) => r.file_type === 'agent');
    if (droppedAgents.length > 0) {
      if (!plan.agents) {
        plan.agents = {};
      }
      for (const agent of droppedAgents) {
        // Use name as the key, content as instruction
        plan.agents[agent.name] = {
          instruction: agent.content || undefined,
        };
      }
    }

    // Add dropped contexts from profile resources
    const droppedContexts = droppedResources.filter((r) => r.file_type === 'context');
    if (droppedContexts.length > 0) {
      // Store contexts in the mount plan under a custom key
      // since these are profile-level context files (markdown content)
      plan.contexts = droppedContexts.map((ctx) => ({
        name: ctx.name,
        path: ctx.path,
        content: ctx.content,
      }));
    }

    return plan;
  };

  // Memoized current mount plan for live preview
  const currentMountPlan = useMemo(() => buildMountPlan(), [sessionSettings, builderState, droppedResources]);

  // Sync JSON text when switching to JSON view or when mount plan changes
  useEffect(() => {
    if (viewMode === 'json') {
      setJsonEditText(JSON.stringify(currentMountPlan, null, 2));
      setJsonEditError(null);
    }
  }, [viewMode, currentMountPlan]);

  // Launch session with built plan
  const handleLaunch = () => {
    if (builderState.providers.length === 0) {
      alert('Please add at least one provider');
      return;
    }
    const plan = buildMountPlan();
    onLaunch(plan);
  };

  const renderDropZone = (
    zone: keyof Omit<BuilderState, 'agents'>,
    title: string,
    icon: typeof Zap,
    color: string
  ) => {
    const Icon = icon;
    const items = builderState[zone];

    return (
      <div
        className={`builder-zone ${dragOverZone === zone ? 'drag-over' : ''} ${items.length > 0 ? 'has-items' : ''}`}
        onDragOver={(e) => handleDragOver(e, zone)}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(e, zone)}
      >
        <div className="zone-header" style={{ color }}>
          <Icon size={14} />
          <span>{title}</span>
          <span className="zone-count">({items.length})</span>
        </div>

        <div className="zone-content">
          {items.length === 0 ? (
            <div className="zone-empty">Drop {zone.replace(/s$/, '')}s here</div>
          ) : (
            items.map((item, index) => (
              <div
                key={item.id}
                className={`zone-item ${selectedModule?.zone === zone && selectedModule?.index === index ? 'selected' : ''}`}
              >
                <div className="zone-item-header">
                  <Icon size={12} style={{ color }} />
                  <span className="zone-item-name">{item.module}</span>
                  <div className="zone-item-actions">
                    <button
                      onClick={() => selectModuleForEdit(zone, index)}
                      className="zone-item-btn"
                      title="Configure"
                    >
                      <Settings size={12} />
                    </button>
                    <button
                      onClick={() => removeModule(zone, index)}
                      className="zone-item-btn danger"
                      title="Remove"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
                {item.config && (
                  <div className="zone-item-config">
                    {Object.entries(item.config).map(([key, value]) => (
                      <span key={key} className="config-tag">
                        {key}: {JSON.stringify(value)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="builder-overlay" onClick={onClose}>
      <div className="builder-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="builder-header">
          <h2>Mount Plan Builder</h2>
          <div className="builder-header-actions">
            {/* View Mode Toggle */}
            <div className="view-toggle">
              <button
                onClick={() => setViewMode('builder')}
                className={`toggle-btn ${viewMode === 'builder' ? 'active' : ''}`}
                title="Builder view"
              >
                <Blocks size={14} />
                Builder
              </button>
              <button
                onClick={() => setViewMode('json')}
                className={`toggle-btn ${viewMode === 'json' ? 'active' : ''}`}
                title="JSON view"
              >
                <Code size={14} />
                JSON
              </button>
            </div>
            <button
              onClick={() => setShowProfileImport(!showProfileImport)}
              className="button secondary"
              title="Import from profile"
            >
              <FileText size={14} />
              Import from Profile
            </button>
            <button onClick={onClose} className="close-btn" aria-label="Close">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Profile Import Dropdown */}
        {showProfileImport && (
          <div className="profile-import-dropdown">
            <div className="profile-import-header">
              <span>Select a profile to import modules from:</span>
            </div>
            <div className="profile-import-list">
              {profiles.length === 0 ? (
                <div className="no-profiles">No profiles available</div>
              ) : (
                profiles.map((profile) => (
                  <button
                    key={profile.path}
                    className="profile-import-item"
                    onClick={() => importFromProfile(profile.name)}
                  >
                    <FileText size={14} />
                    <span className="profile-name">{profile.name}</span>
                    {profile.collection && <span className="profile-collection">{profile.collection}</span>}
                  </button>
                ))
              )}
            </div>
          </div>
        )}

        <div className="builder-content">
          {viewMode === 'json' ? (
            /* JSON View */
            <div className="json-view-container">
              <div className="json-view-header">
                <h3>Edit Mount Plan JSON</h3>
                <p className="json-view-description">
                  Edit the JSON directly and apply changes to update the builder
                </p>
              </div>
              <textarea
                className={`json-view-content json-editor ${jsonEditError ? 'has-error' : ''}`}
                value={jsonEditText}
                onChange={(e) => {
                  setJsonEditText(e.target.value);
                  setJsonEditError(null);
                }}
                spellCheck={false}
              />
              {jsonEditError && (
                <div className="json-error">
                  <span className="error-icon">!</span>
                  {jsonEditError}
                </div>
              )}
              <div className="json-view-actions">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(jsonEditText);
                  }}
                  className="button secondary"
                >
                  Copy to Clipboard
                </button>
                <button
                  onClick={applyJsonChanges}
                  className="button secondary"
                >
                  Apply Changes
                </button>
                <button
                  onClick={handleLaunch}
                  disabled={builderState.providers.length === 0}
                  className={`button primary launch-btn ${builderState.providers.length > 0 ? 'ready' : ''}`}
                >
                  <Play size={16} />
                  Launch Session
                </button>
              </div>
            </div>
          ) : (
            <>
          {/* Module Palette (left sidebar) */}
          <div className="module-palette">
            <div className="palette-search">
              <Search size={14} />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search modules..."
              />
            </div>

            {loading ? (
              <div className="palette-loading">Loading modules...</div>
            ) : (
              <div className="palette-categories">
                {(['provider', 'tool', 'hook'] as const).map((category) => {
                  const Icon = CATEGORY_ICONS[category];
                  const color = CATEGORY_COLORS[category];
                  const categoryModules = modulesByCategory[category];
                  const isExpanded = expandedCategory === category;

                  return (
                    <div key={category} className="palette-category">
                      <button
                        className="category-header"
                        onClick={() => setExpandedCategory(isExpanded ? null : category)}
                        style={{ color }}
                      >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        <Icon size={14} />
                        <span className="category-name">{category}s</span>
                        <span className="category-count">({categoryModules.length})</span>
                      </button>

                      {isExpanded && (
                        <div className="category-modules">
                          {categoryModules.length === 0 ? (
                            <div className="no-modules">No {category}s found</div>
                          ) : (
                            categoryModules.map((module) => (
                              <div
                                key={module.id}
                                className="palette-module"
                                draggable
                                onDragStart={(e) => handleDragStart(e, module)}
                              >
                                <Icon size={12} style={{ color }} />
                                <div className="module-info">
                                  <span className="module-id">{module.id}</span>
                                  {module.description && (
                                    <span className="module-desc">{module.description}</span>
                                  )}
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Agents Section - Shows all agents from all collections */}
                {(() => {
                  const allAgents = availableResources.filter((r) => r.file_type === 'agent');
                  if (allAgents.length === 0) return null;

                  const AgentIcon = CATEGORY_ICONS['profile-agent'];
                  const agentColor = CATEGORY_COLORS['profile-agent'];
                  const isExpanded = expandedCategory === 'profile-agent';

                  return (
                    <div className="palette-category">
                      <button
                        className="category-header"
                        onClick={() => setExpandedCategory(isExpanded ? null : 'profile-agent')}
                        style={{ color: agentColor }}
                      >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        <AgentIcon size={14} />
                        <span className="category-name">agents</span>
                        <span className="category-count">({allAgents.length})</span>
                      </button>

                      {isExpanded && (
                        <div className="category-modules">
                          {allAgents.map((resource) => (
                            <div
                              key={resource.path}
                              className="palette-module profile-resource"
                              draggable
                              onDragStart={(e) => handleProfileResourceDragStart(e, resource)}
                            >
                              <AgentIcon size={12} style={{ color: agentColor }} />
                              <div className="module-info">
                                <span className="module-id">{resource.name}</span>
                                <span className="module-desc">{resource.path}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Context Files Section - Shows all context files from all collections */}
                {(() => {
                  const allContexts = availableResources.filter((r) => r.file_type === 'context');
                  if (allContexts.length === 0) return null;

                  const ContextIcon = CATEGORY_ICONS['profile-context'];
                  const contextColor = CATEGORY_COLORS['profile-context'];
                  const isExpanded = expandedCategory === 'profile-context';

                  return (
                    <div className="palette-category">
                      <button
                        className="category-header"
                        onClick={() => setExpandedCategory(isExpanded ? null : 'profile-context')}
                        style={{ color: contextColor }}
                      >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        <ContextIcon size={14} />
                        <span className="category-name">context files</span>
                        <span className="category-count">({allContexts.length})</span>
                      </button>

                      {isExpanded && (
                        <div className="category-modules">
                          {allContexts.map((resource) => (
                            <div
                              key={resource.path}
                              className="palette-module profile-resource"
                              draggable
                              onDragStart={(e) => handleProfileResourceDragStart(e, resource)}
                            >
                              <ContextIcon size={12} style={{ color: contextColor }} />
                              <div className="module-info">
                                <span className="module-id">{resource.name}</span>
                                <span className="module-desc">{resource.path}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            )}
          </div>

          {/* Builder Canvas (center) */}
          <div className="builder-canvas">
            <div className="canvas-instructions">
              Drag modules from the palette to build your mount plan
            </div>

            {/* Session Settings Section */}
            <div className="session-settings">
              <div className="session-settings-header">
                <Settings size={14} />
                <span>SESSION SETTINGS</span>
              </div>
              <div className="session-settings-content">
                <div className="session-settings-row">
                  <div className="session-setting">
                    <label htmlFor="orchestrator">
                      <Cpu size={12} style={{ color: CATEGORY_COLORS.orchestrator }} />
                      Orchestrator
                    </label>
                    <select
                      id="orchestrator"
                      value={sessionSettings.orchestrator}
                      onChange={(e) => setSessionSettings((s) => ({ ...s, orchestrator: e.target.value }))}
                    >
                      {KNOWN_ORCHESTRATORS.map((orch) => (
                        <option key={orch.id} value={orch.id}>
                          {orch.name}
                        </option>
                      ))}
                    </select>
                    <span className="setting-description">
                      {KNOWN_ORCHESTRATORS.find((o) => o.id === sessionSettings.orchestrator)?.description}
                    </span>
                  </div>
                  <div className="session-setting">
                    <label htmlFor="context">
                      <Database size={12} style={{ color: CATEGORY_COLORS.context }} />
                      Context
                    </label>
                    <select
                      id="context"
                      value={sessionSettings.context}
                      onChange={(e) => setSessionSettings((s) => ({ ...s, context: e.target.value }))}
                    >
                      {KNOWN_CONTEXTS.map((ctx) => (
                        <option key={ctx.id} value={ctx.id}>
                          {ctx.name}
                        </option>
                      ))}
                    </select>
                    <span className="setting-description">
                      {KNOWN_CONTEXTS.find((c) => c.id === sessionSettings.context)?.description}
                    </span>
                  </div>
                </div>

                {/* Orchestrator Config */}
                <div className="session-config-editor">
                  <label>
                    <Settings size={12} />
                    Orchestrator Configuration (JSON)
                  </label>
                  <textarea
                    className="config-json-input"
                    placeholder='{"extended_thinking": false}'
                    value={sessionSettings.orchestratorConfig ? JSON.stringify(sessionSettings.orchestratorConfig, null, 2) : ''}
                    onChange={(e) => {
                      try {
                        const parsed = e.target.value.trim() ? JSON.parse(e.target.value) : undefined;
                        setSessionSettings((s) => ({ ...s, orchestratorConfig: parsed }));
                      } catch {
                        // Invalid JSON, keep editing
                      }
                    }}
                    rows={3}
                  />
                </div>

                {/* Context Config */}
                <div className="session-config-editor">
                  <label>
                    <Settings size={12} />
                    Context Configuration (JSON)
                  </label>
                  <textarea
                    className="config-json-input"
                    placeholder='{"max_tokens": 50000}'
                    value={sessionSettings.contextConfig ? JSON.stringify(sessionSettings.contextConfig, null, 2) : ''}
                    onChange={(e) => {
                      try {
                        const parsed = e.target.value.trim() ? JSON.parse(e.target.value) : undefined;
                        setSessionSettings((s) => ({ ...s, contextConfig: parsed }));
                      } catch {
                        // Invalid JSON, keep editing
                      }
                    }}
                    rows={3}
                  />
                </div>
              </div>
            </div>

            <div className="drop-zones">
              {renderDropZone('providers', 'PROVIDERS', Zap, CATEGORY_COLORS.provider)}
              {renderDropZone('tools', 'TOOLS', Wrench, CATEGORY_COLORS.tool)}
              {renderDropZone('hooks', 'HOOKS', GitBranch, CATEGORY_COLORS.hook)}
            </div>

            {/* Profile Resources Section - Drop zone for agents and context files */}
            {/* Positioned after TOOLS/HOOKS for logical grouping */}
            <div
              className={`profile-resources-canvas-section ${dragOverProfileResources ? 'drag-over' : ''} ${droppedResources.length === 0 ? 'empty-zone' : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOverProfileResources(true);
              }}
              onDragLeave={() => setDragOverProfileResources(false)}
              onDrop={handleProfileResourceDrop}
            >
              <div className="profile-resources-canvas-header">
                <FileText size={14} />
                <span>PROFILE RESOURCES</span>
                <span className="zone-count">({droppedResources.length})</span>
              </div>

              {droppedResources.length === 0 ? (
                <div className="profile-resources-empty">
                  Drop profile agents and context files here
                </div>
              ) : (
                <>
                  {/* Profile Agents on Canvas */}
                  {(() => {
                    const profileAgents = droppedResources.filter((r) => r.file_type === 'agent');
                    if (profileAgents.length === 0) return null;

                    return (
                      <div className="profile-canvas-subsection">
                        <div className="profile-canvas-subsection-header">
                          <Bot size={12} style={{ color: CATEGORY_COLORS['profile-agent'] }} />
                          <span>Profile Agents ({profileAgents.length})</span>
                        </div>
                        <div className="profile-canvas-items">
                          {profileAgents.map((resource, _idx) => {
                            const globalIndex = droppedResources.findIndex(
                              (r) => r.path === resource.path && r.file_type === 'agent'
                            );
                            return (
                              <div key={resource.path} className="profile-canvas-item">
                                <Bot size={12} style={{ color: CATEGORY_COLORS['profile-agent'] }} />
                                <div className="profile-canvas-item-info">
                                  <span className="profile-canvas-item-name">{resource.name}</span>
                                  <span className="profile-canvas-item-path">{resource.path}</span>
                                </div>
                                <button
                                  className="profile-canvas-item-remove"
                                  onClick={() => removeProfileResource(globalIndex)}
                                  title="Remove"
                                >
                                  <X size={12} />
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Profile Context Files on Canvas */}
                  {(() => {
                    const profileContexts = droppedResources.filter((r) => r.file_type === 'context');
                    if (profileContexts.length === 0) return null;

                    return (
                      <div className="profile-canvas-subsection">
                        <div className="profile-canvas-subsection-header">
                          <FileText size={12} style={{ color: CATEGORY_COLORS['profile-context'] }} />
                          <span>Context Files ({profileContexts.length})</span>
                        </div>
                        <div className="profile-canvas-items">
                          {profileContexts.map((resource, _idx) => {
                            const globalIndex = droppedResources.findIndex(
                              (r) => r.path === resource.path && r.file_type === 'context'
                            );
                            return (
                              <div key={resource.path} className="profile-canvas-item">
                                <FileText size={12} style={{ color: CATEGORY_COLORS['profile-context'] }} />
                                <div className="profile-canvas-item-info">
                                  <span className="profile-canvas-item-name">{resource.name}</span>
                                  <span className="profile-canvas-item-path">{resource.path}</span>
                                </div>
                                <button
                                  className="profile-canvas-item-remove"
                                  onClick={() => removeProfileResource(globalIndex)}
                                  title="Remove"
                                >
                                  <X size={12} />
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })()}
                </>
              )}
            </div>

            {/* Agents Section */}
            <div
              className={`agents-section ${dragOverAgents ? 'drag-over' : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'copy';
                setDragOverAgents(true);
              }}
              onDragLeave={() => setDragOverAgents(false)}
              onDrop={handleAgentDrop}
            >
              <div className="agents-header">
                <Bot size={14} />
                <span>AGENTS</span>
                <span className="zone-count">({builderState.agents.length})</span>
                {dragOverAgents && <span className="drop-indicator">Drop agent here</span>}
              </div>

              <div className="agents-content">
                {/* Agent Form */}
                <div className="agent-form">
                  <div className="agent-form-row">
                    <input
                      type="text"
                      value={agentForm.name}
                      onChange={(e) => setAgentForm((f) => ({ ...f, name: e.target.value }))}
                      placeholder="Agent name"
                      className="agent-input"
                    />
                    <input
                      type="text"
                      value={agentForm.description}
                      onChange={(e) => setAgentForm((f) => ({ ...f, description: e.target.value }))}
                      placeholder="Description (optional)"
                      className="agent-input"
                    />
                  </div>
                  <div className="agent-form-row">
                    <input
                      type="text"
                      value={agentForm.tools}
                      onChange={(e) => setAgentForm((f) => ({ ...f, tools: e.target.value }))}
                      placeholder="Tools (comma-separated, e.g., tool-filesystem, tool-shell)"
                      className="agent-input full"
                    />
                    <button
                      onClick={editingAgent !== null ? updateAgent : addAgent}
                      className="button primary agent-btn"
                    >
                      <Plus size={14} />
                      {editingAgent !== null ? 'Update' : 'Add'}
                    </button>
                    {editingAgent !== null && (
                      <button
                        onClick={() => {
                          setEditingAgent(null);
                          setAgentForm({ name: '', description: '', tools: '' });
                        }}
                        className="button secondary agent-btn"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>

                {/* Agent List */}
                {builderState.agents.length > 0 && (
                  <div className="agents-list">
                    {builderState.agents.map((agent, index) => (
                      <div key={agent.id} className="agent-item">
                        <div className="agent-item-header">
                          <Bot size={12} style={{ color: '#8b5cf6' }} />
                          <span className="agent-name">{agent.name}</span>
                          <div className="agent-item-actions">
                            <button
                              onClick={() => editAgent(index)}
                              className="zone-item-btn"
                              title="Edit"
                            >
                              <Settings size={12} />
                            </button>
                            <button
                              onClick={() => removeAgent(index)}
                              className="zone-item-btn danger"
                              title="Remove"
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </div>
                        {(agent.description || agent.tools.length > 0) && (
                          <div className="agent-item-details">
                            {agent.description && (
                              <span className="agent-description">{agent.description}</span>
                            )}
                            {agent.tools.length > 0 && (
                              <div className="agent-tools">
                                {agent.tools.map((tool) => (
                                  <span key={tool} className="config-tag">
                                    {tool}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {builderState.agents.length === 0 && (
                  <div className="agents-empty">
                    No agents defined. Add agents for sub-session delegation.
                  </div>
                )}
              </div>
            </div>

            {/* Launch Button */}
            <div className="builder-actions">
              <button
                onClick={handleLaunch}
                disabled={builderState.providers.length === 0}
                className={`button primary launch-btn ${builderState.providers.length > 0 ? 'ready' : ''}`}
              >
                <Play size={16} />
                Launch Session
              </button>
            </div>
          </div>

          {/* Config Editor (right sidebar, shown when module selected) */}
          {selectedModule && (
            <div className="config-editor">
              <div className="config-header">
                <h3>Configure Module</h3>
                <button onClick={() => setSelectedModule(null)} className="close-btn small">
                  <X size={14} />
                </button>
              </div>
              <div className="config-module-name">
                {builderState[selectedModule.zone][selectedModule.index]?.module}
              </div>
              {builderState[selectedModule.zone][selectedModule.index]?.source && (
                <div className="config-module-source">
                  {builderState[selectedModule.zone][selectedModule.index]?.source}
                </div>
              )}
              <textarea
                value={configInput}
                onChange={(e) => setConfigInput(e.target.value)}
                placeholder='{"key": "value"}'
                className="config-textarea"
                rows={10}
              />
              <div className="config-actions">
                <button onClick={() => setSelectedModule(null)} className="button secondary">
                  Cancel
                </button>
                <button onClick={handleSaveConfig} className="button primary">
                  Save Config
                </button>
              </div>
            </div>
          )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
