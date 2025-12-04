import { useState } from 'react';
import './HelpModal.css';

interface HelpModalProps {
  onClose: () => void;
}

export function HelpModal({ onClose }: HelpModalProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyInstallCommand = (packageName: string, id: string) => {
    const command = `uv add git+https://github.com/${packageName}`;
    navigator.clipboard.writeText(command);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="help-modal-overlay" onClick={onClose}>
      <div className="help-modal" onClick={(e) => e.stopPropagation()}>
        <div className="help-modal-header">
          <h2>Amplifier Playground</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="help-modal-content">
          <section>
            <h3>What is this?</h3>
            <p>
              Amplifier Playground is an interactive environment for building and testing
              AI agent sessions. Browse profiles, explore their dependencies, and test
              configurations before deploying.
            </p>
          </section>

          <section>
            <h3>Key Concepts</h3>

            <div className="concept">
              <h4>Profiles</h4>
              <p>
                Profiles define how an AI session is configured - which model to use,
                what tools are available, and what context to include. They live in
                <code>.amplifier/profiles/</code> in your project.
              </p>
            </div>

            <div className="concept">
              <h4>Collections</h4>
              <p>
                Collections are packages of reusable profiles, agents, and context files.
                Install collections to get pre-built configurations you can extend.
              </p>
            </div>

            <div className="concept">
              <h4>Context Files</h4>
              <p>
                Context files (<code>@context/</code>) contain project-specific information
                that gets included in the AI's context. Use them for coding standards,
                API docs, or any persistent knowledge.
              </p>
            </div>

            <div className="concept">
              <h4>Agents</h4>
              <p>
                Agents are specialized AI personas with specific expertise. Include them
                in profiles to get focused help for tasks like code review or testing.
              </p>
            </div>
          </section>

          <section>
            <h3>Using the Playground</h3>
            <ol>
              <li><strong>Select a profile</strong> from the dropdown</li>
              <li><strong>Click "View Graph"</strong> to explore its dependencies</li>
              <li><strong>Start a session</strong> to test the configuration</li>
              <li><strong>Add panes</strong> to compare multiple profiles</li>
            </ol>
          </section>

          <section>
            <h3>Installing Collections</h3>
            <p>Add more profiles by installing collections:</p>
            <pre><code># Install official collections
uv add amplifier-collections

# Or install specific collections
uv add amplifier-collection-foundation
uv add amplifier-collection-developer</code></pre>
          </section>

          <section>
            <h3>Reference Collections</h3>
            <p>
              Explore these collections for reference implementations and best practices:
            </p>

            <div className="collections-grid">
              <div className="collection-card">
                <h4>toolkit</h4>
                <p>Building sophisticated CLI tools using metacognitive recipes</p>
                <div className="collection-card-actions">
                  <a href="https://github.com/microsoft/amplifier-collection-toolkit" target="_blank" rel="noopener noreferrer">
                    View →
                  </a>
                  <button
                    className="copy-install-btn"
                    onClick={() => copyInstallCommand('microsoft/amplifier-collection-toolkit', 'toolkit')}
                  >
                    {copiedId === 'toolkit' ? 'Copied!' : 'Copy Install'}
                  </button>
                </div>
              </div>

              <div className="collection-card">
                <h4>design-intelligence</h4>
                <p>Comprehensive design intelligence with specialized agents</p>
                <div className="collection-card-actions">
                  <a href="https://github.com/microsoft/amplifier-collection-design-intelligence" target="_blank" rel="noopener noreferrer">
                    View →
                  </a>
                  <button
                    className="copy-install-btn"
                    onClick={() => copyInstallCommand('microsoft/amplifier-collection-design-intelligence', 'design-intelligence')}
                  >
                    {copiedId === 'design-intelligence' ? 'Copied!' : 'Copy Install'}
                  </button>
                </div>
              </div>

              <div className="collection-card">
                <h4>recipes</h4>
                <p>Multi-step AI agent orchestration for repeatable workflows</p>
                <div className="collection-card-actions">
                  <a href="https://github.com/microsoft/amplifier-collection-recipes" target="_blank" rel="noopener noreferrer">
                    View →
                  </a>
                  <button
                    className="copy-install-btn"
                    onClick={() => copyInstallCommand('microsoft/amplifier-collection-recipes', 'recipes')}
                  >
                    {copiedId === 'recipes' ? 'Copied!' : 'Copy Install'}
                  </button>
                </div>
              </div>

              <div className="collection-card">
                <h4>issues</h4>
                <p>Issue management and tracking workflows</p>
                <div className="collection-card-actions">
                  <a href="https://github.com/microsoft/amplifier-collection-issues" target="_blank" rel="noopener noreferrer">
                    View →
                  </a>
                  <button
                    className="copy-install-btn"
                    onClick={() => copyInstallCommand('microsoft/amplifier-collection-issues', 'issues')}
                  >
                    {copiedId === 'issues' ? 'Copied!' : 'Copy Install'}
                  </button>
                </div>
              </div>
            </div>

            <p className="community-note">
              <strong>Community collections:</strong>{' '}
              <a href="https://github.com/robotdad/amplifier-collection-ddd" target="_blank" rel="noopener noreferrer">
                collection-ddd
              </a>
              <button
                className="copy-install-btn-inline"
                onClick={() => copyInstallCommand('robotdad/amplifier-collection-ddd', 'ddd')}
              >
                {copiedId === 'ddd' ? 'Copied!' : 'Install'}
              </button>
              {' · '}
              <a href="https://github.com/robotdad/amplifier-collection-spec-kit" target="_blank" rel="noopener noreferrer">
                collection-spec-kit
              </a>
              <button
                className="copy-install-btn-inline"
                onClick={() => copyInstallCommand('robotdad/amplifier-collection-spec-kit', 'spec-kit')}
              >
                {copiedId === 'spec-kit' ? 'Copied!' : 'Install'}
              </button>
            </p>

            <p>
              <a href="https://microsoft.github.io/amplifier-docs/showcase/#collections" target="_blank" rel="noopener noreferrer">
                Browse all collections →
              </a>
            </p>
          </section>

          <section>
            <h3>CLI Commands</h3>
            <pre><code># Launch web UI (this app)
amplay

# Run a CLI session
amplay session run foundation:base

# Browse profiles
amplay profiles list</code></pre>
          </section>

          <section>
            <h3>Learn More</h3>
            <p>
              <a href="https://github.com/anthropics/amplifier" target="_blank" rel="noopener noreferrer">
                GitHub Repository
              </a>
              {' · '}
              <a href="https://github.com/anthropics/amplifier#readme" target="_blank" rel="noopener noreferrer">
                Documentation
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
