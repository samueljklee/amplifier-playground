---
profile:
  name: example-with-agents
  version: 1.0.0
  description: Profile with agent definitions for specialized tasks

session:
  orchestrator:
    module: loop-streaming
    config:
      extended_thinking: false
  context:
    module: context-simple
    config:
      max_tokens: 100000

providers:
  - module: provider-anthropic
    config:
      model: claude-sonnet-4-20250514

tools:
  - module: tool-filesystem
  - module: tool-bash

agents:
  - code-reviewer
  - test-writer
---

# Profile with Agents

This profile includes agent definitions for specialized tasks. Agents are reusable AI personas with specific expertise.

## Included Agents

### code-reviewer
Reviews code for quality, bugs, and best practices.

### test-writer
Generates comprehensive test cases for your code.

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
