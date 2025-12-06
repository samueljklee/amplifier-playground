---
profile:
  name: example-local-module
  version: 1.0.0
  description: Example profile using a locally-developed module (tool-echo)

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

tools:
  # Local module from examples/modules/amplifier-module-tool-echo
  # To use this profile, first install the local module:
  #   cd examples/modules/amplifier-module-tool-echo && pip install -e .
  - module: tool-echo
    config:
      prefix: "[Echo] "
---

# Local Module Example

This profile demonstrates using a locally-developed module. The `tool-echo` module provides simple echo and time tools for testing.

## Setup

Before using this profile, install the local module:

```bash
cd examples/modules/amplifier-module-tool-echo
pip install -e .
```

## Available Tools

- **echo**: Echo back messages with optional transformations (upper, lower, reverse)
- **current_time**: Get the current time in various formats (iso, human, unix)

## Use Case

Use this pattern when:
- Developing and testing new modules locally
- Iterating on module functionality before publishing
- Demonstrating module development workflow
