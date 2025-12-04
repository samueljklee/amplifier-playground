---
profile:
  name: example-full
  version: 1.0.0
  description: Complete example combining extends, context, and agents
  extends: foundation:base

tools:
  - module: tool-filesystem
  - module: tool-bash

agents:
  - code-reviewer
---

# Full Example Profile

This profile demonstrates all features together:
- **Extends** `foundation:base` for core configuration
- **References local context** for project-specific rules
- **Includes agents** for specialized tasks

## Project Context

Follow these guidelines when working on this project:

@context/project-rules.md
@context/api-guidelines.md

## What This Profile Does

1. Inherits session and provider config from `foundation:base`
2. Adds filesystem and bash tools for development
3. Loads project rules and API guidelines as context
4. Makes the `code-reviewer` agent available

**Use this pattern when:**
- You want the full power of Amplifier's configuration system
- You're building a production-ready development environment
- You need to combine multiple configuration sources
