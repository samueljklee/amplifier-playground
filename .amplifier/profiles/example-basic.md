---
profile:
  name: example-basic
  version: 1.0.0
  description: Minimal standalone profile - no extends, no agents

session:
  orchestrator:
    module: loop-streaming
    config:
      extended_thinking: false
  context:
    module: context-simple
    config:
      max_tokens: 50000

providers:
  - module: provider-anthropic
    config:
      model: claude-sonnet-4-20250514

tools: []
---

# Basic Profile Example

This is the simplest possible profile. It defines everything inline without extending other profiles or using agents.

**Use this pattern when:**
- Starting a new project
- You want full control over configuration
- You don't need to share configuration across profiles
