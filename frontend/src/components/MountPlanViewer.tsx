import { useState } from 'react';
import { Zap, Wrench, Anchor, Bot, Copy, Check, ChevronRight, ChevronDown, WrapText } from 'lucide-react';
import type { MountPlan, ModuleEntry, AgentConfig } from '../types';
import './MountPlanViewer.css';

interface MountPlanViewerProps {
  plan: MountPlan | null;
}

function ModuleIcon({ type }: { type: 'provider' | 'tool' | 'hook' | 'agent' }) {
  const iconProps = { size: 14, className: `module-icon module-icon-${type}` };
  switch (type) {
    case 'provider': return <Zap {...iconProps} />;
    case 'tool': return <Wrench {...iconProps} />;
    case 'hook': return <Anchor {...iconProps} />;
    case 'agent': return <Bot {...iconProps} />;
  }
}

function ConfigDisplay({ config }: { config: Record<string, unknown> | undefined }) {
  if (!config || Object.keys(config).length === 0) {
    return <span className="no-config">No configuration</span>;
  }

  const entries = Object.entries(config);

  // For simple configs (1-2 primitive values), show inline
  if (entries.length <= 2 && entries.every(([, v]) => typeof v !== 'object' || v === null)) {
    return (
      <span className="config-inline">
        {entries.map(([k, v], idx) => (
          <span key={k}>
            <span className="config-key">{k}:</span>{' '}
            <span className="config-value">{JSON.stringify(v)}</span>
            {idx < entries.length - 1 && ', '}
          </span>
        ))}
      </span>
    );
  }

  // For complex configs, show as formatted JSON
  return (
    <pre className="config-block">
      {JSON.stringify(config, null, 2)}
    </pre>
  );
}

function ModuleCard({
  module,
  type,
  defaultExpanded = false
}: {
  module: ModuleEntry;
  type: 'provider' | 'tool' | 'hook';
  defaultExpanded?: boolean;
}) {
  const hasConfig = module.config && Object.keys(module.config).length > 0;
  const isSimpleConfig = hasConfig && Object.keys(module.config!).length <= 2 &&
    Object.values(module.config!).every(v => typeof v !== 'object' || v === null);

  const [expanded, setExpanded] = useState(defaultExpanded || isSimpleConfig);

  return (
    <div className={`module-card ${expanded ? 'expanded' : ''}`}>
      <div
        className="module-card-header"
        onClick={() => hasConfig && !isSimpleConfig && setExpanded(!expanded)}
      >
        <ModuleIcon type={type} />
        <span className="module-name">{module.module}</span>
        {hasConfig && !isSimpleConfig && (
          <span className="expand-icon">
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        )}
      </div>
      {(expanded || isSimpleConfig) && hasConfig && (
        <div className="module-card-config">
          <ConfigDisplay config={module.config} />
        </div>
      )}
    </div>
  );
}

function AgentCard({ name, config }: { name: string; config: AgentConfig }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = config.description || config.session || config.tools;

  return (
    <div className={`module-card ${expanded ? 'expanded' : ''}`}>
      <div
        className="module-card-header"
        onClick={() => hasDetails && setExpanded(!expanded)}
      >
        <ModuleIcon type="agent" />
        <span className="module-name">{name}</span>
        {config.description && (
          <span className="agent-description">{config.description}</span>
        )}
        {hasDetails && (
          <span className="expand-icon">
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        )}
      </div>
      {expanded && hasDetails && (
        <div className="module-card-config">
          <pre className="config-block">
            {JSON.stringify(config, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function Section({
  title,
  count,
  type,
  children
}: {
  title: string;
  count: number;
  type: 'provider' | 'tool' | 'hook' | 'agent';
  children: React.ReactNode;
}) {
  if (count === 0) {
    return (
      <div className="mount-plan-section empty">
        <div className="section-header">
          <span className={`section-title section-title-${type}`}>{title}</span>
          <span className="section-count">(0)</span>
        </div>
        <div className="section-empty">No {title.toLowerCase()} configured</div>
      </div>
    );
  }

  return (
    <div className={`mount-plan-section section-${type}`}>
      <div className="section-header">
        <span className={`section-title section-title-${type}`}>{title}</span>
        <span className="section-count">({count})</span>
      </div>
      <div className="section-content">
        {children}
      </div>
    </div>
  );
}

export function MountPlanViewer({ plan }: MountPlanViewerProps) {
  const [copied, setCopied] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const [wordWrap, setWordWrap] = useState(false);

  if (!plan) {
    return (
      <div className="mount-plan-viewer">
        <div className="mount-plan-empty">
          Mount plan not available. The profile may have compilation errors.
        </div>
      </div>
    );
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(plan, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const providers = plan.providers || [];
  const tools = plan.tools || [];
  const hooks = plan.hooks || [];
  const agents = plan.agents || {};
  const agentEntries = Object.entries(agents);

  if (showRaw) {
    return (
      <div className="mount-plan-viewer">
        <div className="mount-plan-actions">
          <button onClick={() => setShowRaw(false)} className="button small">
            Structured View
          </button>
          <button onClick={() => setWordWrap(!wordWrap)} className={`button small ${wordWrap ? 'active' : ''}`}>
            <WrapText size={14} />
            Wrap
          </button>
          <button onClick={handleCopy} className="button small">
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? 'Copied!' : 'Copy JSON'}
          </button>
        </div>
        <pre className={`mount-plan-raw ${wordWrap ? 'wrap' : ''}`}>
          {JSON.stringify(plan, null, 2)}
        </pre>
      </div>
    );
  }

  return (
    <div className="mount-plan-viewer">
      {/* Session section */}
      {plan.session && (
        <div className="mount-plan-section session-section">
          <div className="section-header">
            <span className="section-title">SESSION</span>
          </div>
          <div className="session-content">
            {plan.session.orchestrator && (
              <div className="session-item">
                <span className="session-label">Orchestrator</span>
                <span className="session-value">
                  {typeof plan.session.orchestrator === 'string'
                    ? plan.session.orchestrator
                    : plan.session.orchestrator.module}
                </span>
              </div>
            )}
            {plan.session.context && (
              <div className="session-item">
                <span className="session-label">Context</span>
                <span className="session-value">
                  {typeof plan.session.context === 'string'
                    ? plan.session.context
                    : plan.session.context.module}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Providers */}
      <Section title="PROVIDERS" count={providers.length} type="provider">
        {providers.map((p, idx) => (
          <ModuleCard key={`${p.module}-${idx}`} module={p} type="provider" defaultExpanded={true} />
        ))}
      </Section>

      {/* Tools */}
      <Section title="TOOLS" count={tools.length} type="tool">
        {tools.map((t, idx) => (
          <ModuleCard key={`${t.module}-${idx}`} module={t} type="tool" />
        ))}
      </Section>

      {/* Hooks */}
      <Section title="HOOKS" count={hooks.length} type="hook">
        {hooks.map((h, idx) => (
          <ModuleCard key={`${h.module}-${idx}`} module={h} type="hook" />
        ))}
      </Section>

      {/* Agents */}
      <Section title="AGENTS" count={agentEntries.length} type="agent">
        {agentEntries.map(([name, config]) => (
          <AgentCard key={name} name={name} config={config} />
        ))}
      </Section>

      {/* Actions footer */}
      <div className="mount-plan-actions">
        <button onClick={handleCopy} className="button small">
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied ? 'Copied!' : 'Copy JSON'}
        </button>
        <button onClick={() => setShowRaw(true)} className="button small secondary">
          View Raw
        </button>
      </div>
    </div>
  );
}
