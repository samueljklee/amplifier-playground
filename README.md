# Amplifier Workbench

Interactive mount plan builder and tester for Amplifier. Build, configure, and test AI agent sessions with a web interface for humans and CLI for coding agents.

## Installation

```bash
cd amplifier-workbench
uv sync
```

## Usage

### CLI

The CLI command is `awb` (Amplifier WorkBench).

#### Module Discovery

```bash
# List all available modules
awb modules list

# List by category
awb modules list -c provider
awb modules list -c tool

# Get module info
awb modules info provider-anthropic

# Register a local development module
awb modules register ./my-module \
    --id my-custom-tool \
    --name "My Custom Tool" \
    --category tool \
    --description "A tool I'm developing"
```

#### Configuration Management

```bash
# Create a new configuration
awb config create "My Test Config" -d "Testing anthropic provider"

# Create from a JSON file (see examples/mount-plan.json)
awb config create "From File" -f ./examples/mount-plan.json

# Create from an amplifier profile
awb config create "From Profile" -p default-chat

# List configurations
awb config list
awb config list -t testing  # filter by tag

# Show configuration details
awb config show my-test-config

# Export configuration as JSON
awb config export my-test-config -o exported.json

# Delete configuration
awb config delete my-test-config
```

#### Running Sessions

```bash
# Run a session with a saved config
awb session run my-test-config -p "Hello, how are you?"

# Interactive mode
awb session run my-test-config -i

# Stream events as JSONL (useful for agents)
awb session run my-test-config -p "Test prompt" -e

# Quick test a mount plan file without saving
awb session test ./mount-plan.json -p "Test this configuration"

# Use modules from a local development directory (dynamic resolution)
awb session run my-config -p "Hello" -m ../amplifier-dev
awb session test ./mount-plan.json -p "Test" -m ../amplifier-dev
```

**Note on `--modules-dir` / `-m`**: This option enables runtime module resolution from a development workspace. Point it at a directory containing `amplifier-module-*` folders (e.g., `amplifier-module-provider-anthropic/`). Modules don't need to be installed as packages - the workbench will load them directly from the filesystem.

### Web API

Start the development server:

```bash
uvicorn amplifier_workbench.web.app:app --reload
```

The API is available at `http://localhost:8000` with:
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

#### API Endpoints

**Modules**
- `GET /api/modules` - List available modules
- `GET /api/modules/{id}` - Get module details
- `POST /api/modules/register` - Register a local module

**Configurations**
- `GET /api/configs` - List saved configurations
- `POST /api/configs` - Create a new configuration
- `GET /api/configs/{id}` - Get configuration details
- `PUT /api/configs/{id}` - Update a configuration
- `DELETE /api/configs/{id}` - Delete a configuration

**Sessions**
- `POST /api/sessions` - Create and start a session
- `GET /api/sessions` - List active sessions
- `GET /api/sessions/{id}` - Get session info
- `DELETE /api/sessions/{id}` - Stop a session
- `POST /api/sessions/{id}/prompt` - Send a prompt
- `POST /api/sessions/{id}/approval` - Resolve an approval request
- `GET /api/sessions/{id}/events` - Stream events via SSE

#### Example: Create and Use a Session

```bash
# Create a configuration
curl -X POST http://localhost:8000/api/configs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Config",
    "mount_plan": {
      "session": {
        "orchestrator": "loop-basic",
        "context": "context-simple"
      },
      "providers": [
        {"module": "provider-anthropic", "config": {"model": "claude-3-5-sonnet-20241022"}}
      ],
      "tools": [
        {"module": "tool-filesystem"}
      ],
      "hooks": []
    }
  }'

# Create a session
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"config_id": "test-config"}'

# Create a session with runtime module resolution
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"config_id": "test-config", "modules_dir": "/path/to/amplifier-dev"}'

# Send a prompt
curl -X POST http://localhost:8000/api/sessions/{session_id}/prompt \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, what can you do?"}'

# Stream events (in another terminal)
curl -N http://localhost:8000/api/sessions/{session_id}/events
```

### As a Library

The core components can be imported directly:

```python
import asyncio
from amplifier_workbench.core import (
    ConfigManager,
    ModuleRegistry,
    SessionRunner,
    create_cli_event_callback,
)

async def main():
    # Discover modules
    registry = ModuleRegistry()
    providers = registry.list_by_category("provider")
    print(f"Found {len(providers)} providers")

    # Load or create a configuration
    config_manager = ConfigManager()
    cfg = config_manager.get_config("my-config")

    if not cfg:
        cfg = config_manager.create_config(
            name="my-config",
            mount_plan={
                "session": {"orchestrator": "loop-basic", "context": "context-simple"},
                "providers": [{"module": "provider-anthropic"}],
                "tools": [],
                "hooks": [],
            }
        )

    # Run a session with event streaming
    async def my_event_handler(event: str, data: dict):
        print(f"Event: {event}")

    async with SessionRunner(
        mount_plan=cfg.mount_plan,
        event_callback=my_event_handler,
        approval_mode="auto",
        modules_dir="../amplifier-dev",  # Optional: load modules from dev workspace
    ) as runner:
        response = await runner.prompt("Hello!")
        print(response)

asyncio.run(main())
```

## Architecture

```
amplifier-workbench/
├── src/amplifier_workbench/
│   ├── core/                    # Core library (used by CLI and Web)
│   │   ├── module_registry.py   # Module discovery and registration
│   │   ├── config_manager.py    # File-based config storage
│   │   ├── session_runner.py    # Session management with events
│   │   ├── ux_systems.py        # Approval and display systems
│   │   └── protocols.py         # EventCallback protocol
│   ├── cli/                     # Click-based CLI
│   │   └── main.py              # CLI commands
│   └── web/                     # FastAPI web server
│       ├── app.py               # FastAPI application
│       ├── models.py            # Pydantic models
│       └── routes/              # API routes
│           ├── modules.py
│           ├── configs.py
│           └── sessions.py
```

## Configuration Storage

Configurations are stored as JSON files in `~/.amplifier-workbench/configs/`.

## Development

```bash
# Install with dev dependencies
uv sync

# Run tests
uv run pytest

# Run type checking
uv run pyright

# Format code
uv run ruff format .
```

## License

MIT
