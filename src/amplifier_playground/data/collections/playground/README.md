# Playground Collection

Example profiles demonstrating Amplifier Playground features and profile syntax.

## Profiles

- **example-basic** - Minimal standalone profile with no extends or agents
- **example-full** - Complete profile with all common options
- **example-extends** - Profile that extends foundation:base
- **example-with-agents** - Profile demonstrating agent configuration
- **example-with-context** - Profile with context file references

## Usage

```bash
# Run an example profile
amplay session run playground:example-basic

# View profile details
amplay profiles show playground:example-full
```

## Creating Your Own Profiles

Use these examples as templates. Copy and modify them in your project's `.amplifier/profiles/` directory.
