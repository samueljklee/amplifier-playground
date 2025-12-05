---
profile:
  name: example-basic
  version: 1.0.0
  description: Minimal standalone profile - no extends, no agents

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
      max_tokens: 50000

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
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
