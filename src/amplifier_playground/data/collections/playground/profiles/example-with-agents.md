---
profile:
  name: example-with-agents
  version: 1.0.0
  description: Profile with agent definitions for specialized tasks

session:
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/microsoft/amplifier-module-loop-streaming@main
    config:
      extended_thinking: false
  context:
    module: context-simple
    source: git+https://github.com/microsoft/amplifier-module-context-simple@main
    config:
      max_tokens: 100000

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      model: claude-sonnet-4-20250514

tools:
  - module: tool-filesystem
    source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@main

agents:
  - bug-hunter
  - test-coverage
  - researcher
---

# Profile with Agents

This profile includes agent definitions for specialized tasks. Agents are reusable AI personas with specific expertise.

## Included Agents

### bug-hunter
Specialized debugging expert focused on finding and fixing bugs systematically using hypothesis-driven debugging.

### test-coverage
Expert at analyzing test coverage, identifying gaps, and suggesting comprehensive test cases.

### researcher
General-purpose research agent for exploring codebases, searching for code patterns, and answering questions.

## How Agents Work

When you reference an agent in your profile, Amplifier will:
1. Look for the agent definition in `.amplifier/agents/` or collection agents
2. Load the agent's system prompt and configuration
3. Make the agent available during the session

**Use this pattern when:**
- You need specialized AI personas for different tasks
- You want consistent behavior for specific workflows
- You're building a team of AI assistants with different expertise

## Creating Custom Agents

Create agent files in `.amplifier/agents/`:

```markdown
<!-- .amplifier/agents/my-agent.md -->
---
agent:
  name: my-agent
  description: My custom agent
---

You are a specialized assistant for...
```
