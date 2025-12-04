# Amplifier Playground

Interactive environment for building, configuring, and testing Amplifier AI agent sessions. Features a web UI for exploration and a CLI for automation.

## Quickstart

```bash
# Fastest way - run directly from GitHub (no installation needed)
uvx --from git+https://github.com/samueljklee/amplifier-playground amplay

# Or clone for example profiles and development
git clone https://github.com/samueljklee/amplifier-playground
cd amplifier-playground
uv sync
amplay
```

That's it! The web UI opens automatically at `http://localhost:8000`.

> **Note**: Running via `uvx` is the quickest way to try the playground. Clone the repository if you want access to example profiles or want to contribute.

## Profiles vs Mount Plans

**Profiles** are human-readable YAML files that define session configurations. They live in `.amplifier/profiles/` and can extend other profiles, reference modules, and include context files. Profiles are meant for reusable, version-controlled configurations.

**Mount Plans** are the compiled JSON configuration that Amplifier uses to run sessions. When you select a profile, it gets compiled into a mount plan containing the fully-resolved session settings, providers, tools, hooks, and agents.

In the playground, you can:
- **Select a profile** from the dropdown to use an existing configuration
- **Paste mount plan JSON** directly to test configurations without creating a profile

This is useful for:
- Testing mount plans exported from other tools
- Quick experiments without modifying your profile files
- Debugging and inspecting exact session configurations

### CLI Options

```bash
amplay                    # Launch web UI (default)
amplay web                # Same as above
amplay web --no-open      # Start server without opening browser
amplay web --port 8080    # Use different port

amplay session run <profile>   # Run a CLI session
amplay profiles list           # Browse available profiles
amplay modules list            # Browse available modules
amplay collections list        # Browse collections
```

## Installation

### With uvx (recommended)

```bash
uvx amplifier-playground
```

### From Source

```bash
git clone https://github.com/samueljklee/amplifier-playground
cd amplifier-playground
uv sync
```

## CLI Reference

### Module Discovery

```bash
# List all available modules
amplay modules list

# List by category
amplay modules list -c provider
amplay modules list -c tool

# Get module info
amplay modules info provider-anthropic

# Register a local development module
amplay modules register ./my-module \
    --id my-custom-tool \
    --name "My Custom Tool" \
    --category tool \
    --description "A tool I'm developing"
```

### Profile Browsing

```bash
# List profiles from all collections
amplay profiles list

# Filter by collection
amplay profiles list -c foundation

# Show profile details and dependencies
amplay profiles show foundation:base
```

### Running Sessions

```bash
# Run a session with a profile
amplay session run foundation:base -p "Hello, how are you?"

# Interactive mode
amplay session run my-profile -i

# Stream events as JSONL (useful for automation)
amplay session run my-profile -p "Test prompt" -e

# Quick test a mount plan JSON file without saving as a profile
amplay session test ./mount-plan.json -p "Test this configuration"

# Use modules from a local development directory
amplay session run my-profile -p "Hello" -m ../amplifier-dev
```

**Web UI**: You can also paste mount plan JSON directly in the web UI by selecting "Paste mount plan JSON..." from the configuration dropdown.

**Note on `--modules-dir` / `-m`**: This option enables runtime module resolution from a development workspace. Point it at a directory containing `amplifier-module-*` folders (e.g., `amplifier-module-provider-anthropic/`). Modules don't need to be installed as packages - the playground will load them directly from the filesystem.

## Web API

The web UI is backed by a REST API. Start the API server directly:

```bash
uvicorn amplifier_playground.web.app:app --reload
```

- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### API Endpoints

**Modules**
- `GET /api/modules` - List available modules
- `GET /api/modules/{id}` - Get module details

**Profiles**
- `GET /api/profiles` - List profiles from all collections
- `GET /api/profiles/{collection}/{name}` - Get profile details
- `GET /api/profiles/{collection}/{name}/graph` - Get dependency graph

**Collections**
- `GET /api/collections` - List available collections

**Sessions**
- `POST /api/sessions` - Create and start a session
- `GET /api/sessions` - List active sessions
- `GET /api/sessions/{id}` - Get session info
- `DELETE /api/sessions/{id}` - Stop a session
- `POST /api/sessions/{id}/prompt` - Send a prompt
- `POST /api/sessions/{id}/approval` - Resolve an approval request
- `GET /api/sessions/{id}/events` - Stream events via SSE

## As a Library

```python
import asyncio
from amplifier_playground.core import (
    CollectionManager,
    ModuleRegistry,
    SessionRunner,
    create_cli_event_callback,
)

async def main():
    # Discover modules
    registry = ModuleRegistry()
    providers = registry.list_by_category("provider")
    print(f"Found {len(providers)} providers")

    # Run a session with event streaming
    async def my_event_handler(event: str, data: dict):
        print(f"Event: {event}")

    async with SessionRunner(
        mount_plan=my_mount_plan,
        event_callback=my_event_handler,
        approval_mode="auto",
        modules_dir="../amplifier-dev",  # Optional: load from dev workspace
    ) as runner:
        response = await runner.prompt("Hello!")
        print(response)

asyncio.run(main())
```

## Architecture

```
amplifier-playground/
├── src/amplifier_playground/
│   ├── core/                    # Core library (CLI and Web)
│   │   ├── module_registry.py   # Module discovery
│   │   ├── collection_manager.py# Collection management
│   │   ├── session_runner.py    # Session management
│   │   └── ux_systems.py        # Approval and display
│   ├── cli/                     # Click-based CLI
│   │   └── main.py              # CLI commands
│   └── web/                     # FastAPI web server
│       ├── app.py               # FastAPI application
│       └── routes/              # API routes
└── frontend/                    # React web UI
```

## Configuration Storage

User configurations are stored in `~/.amplifier-playground/configs/`.

## Development

```bash
# Install with dev dependencies
uv sync

# Run development servers (frontend + backend with hot reload)
make dev

# Run tests
uv run pytest

# Build for distribution
make package
```

## License

MIT
