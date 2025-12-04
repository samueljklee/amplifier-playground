---
profile:
  name: example-extends
  version: 1.0.0
  description: Profile that extends a collection profile
  extends: foundation:profiles/base.md

tools:
  - module: tool-filesystem
  - module: tool-bash
---

# Profile that Extends a Collection

This profile extends `foundation:base` from the foundation collection, inheriting its session configuration and providers.

We only need to specify what we're adding or overriding - in this case, adding tools.

**What gets inherited from `foundation:base`:**
- Session orchestrator and context configuration
- Provider configuration (Claude model)

**What we add:**
- Filesystem and bash tools for development work

**Use this pattern when:**
- You want to build on a well-tested base configuration
- You want to share common settings across your team
- You want to customize a collection profile for your specific needs

## Installing Collections

To use collection profiles, install them first:

```bash
# Install the foundation collection
uv add amplifier-collection-foundation

# Or install all official collections
uv add amplifier-collections
```
