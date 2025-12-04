---
profile:
  name: example-with-context
  version: 1.0.0
  description: Profile that references local context files

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

tools:
  - module: tool-filesystem
  - module: tool-bash
---

# Profile with Local Context

This profile demonstrates how to reference local context files using @mentions.

## Project Context

Follow the rules defined in our project documentation:

@project:context/project-rules.md
@project:context/api-guidelines.md

**Use this pattern when:**
- You have project-specific guidelines
- You want to share context across multiple profiles
- You need to keep context files version-controlled with your project
