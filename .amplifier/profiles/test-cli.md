---
profile:
  name: test-cli
  version: 1.0.0
  description: CLI test profile

session:
  orchestrator:
    module: loop-simple
    config:
      max_turns: 10
  context:
    module: context-simple

tools:
  - module: tool-filesystem
  - module: tool-web
---

# Test CLI Profile

This profile is for testing the CLI profile compilation.
