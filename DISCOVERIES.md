# DISCOVERIES.md

This file documents non-obvious problems, solutions, and patterns discovered during development of amplifier-workbench. Consult this before implementing solutions to complex problems.

---

## PackageSource.resolve() Returns .dist-info Path Instead of Package Path (2025-12-04)

### Issue

When running a profile that uses installed Python packages (like `loop-streaming`), module resolution failed with:

```
Module 'loop-streaming' has no valid Python package at /path/to/site-packages/amplifier_module_loop_streaming-1.0.0.dist-info
```

The resolver was returning the `.dist-info` metadata directory instead of the actual package directory.

### Root Cause

In `amplifier-module-resolution/sources.py`, the `PackageSource.resolve()` method was using `dist.files[0]` to find the package location:

```python
# Original broken code
if dist.files:
    package_path = Path(str(dist.locate_file(dist.files[0]))).parent
    return package_path
```

The problem: `dist.files` returns files from the package's RECORD file in **alphabetical order**. The RECORD file contains both:
- `.dist-info/` metadata files (METADATA, RECORD, WHEEL, etc.)
- Actual package files (`amplifier_module_loop_streaming/__init__.py`, etc.)

Since `.dist-info` sorts before `amplifier_module_*` alphabetically, the first file was always a metadata file, causing the resolver to return the `.dist-info` directory path instead of the actual package.

### Solution

Filter out `.dist-info` files before selecting the first file:

```python
# Fixed code in sources.py
def resolve(self) -> Path:
    try:
        dist = metadata.distribution(self.package_name)
        if dist.files:
            # Filter out .dist-info files to find actual package files
            package_files = [f for f in dist.files if ".dist-info" not in str(f)]
            if package_files:
                package_path = Path(str(dist.locate_file(package_files[0]))).parent
                return package_path
            # Fallback: use first file if all are .dist-info (shouldn't happen)
            package_path = Path(str(dist.locate_file(dist.files[0]))).parent
            return package_path
        return Path(str(dist.locate_file("")))
    except metadata.PackageNotFoundError:
        raise ModuleResolutionError(...)
```

### Key Learnings

1. **`importlib.metadata.distribution().files` returns alphabetically sorted paths** - Don't assume the first file is representative of the package location.

2. **Python packages have two directories in site-packages**:
   - `package_name/` - The actual code
   - `package_name-version.dist-info/` - Package metadata (METADATA, RECORD, WHEEL, etc.)

3. **The RECORD file lists ALL files** - Both the package files and the .dist-info files are listed together.

### Prevention

- When working with `importlib.metadata`, always filter or validate the file paths you're using
- Test package resolution with real installed packages, not just mocked data
- Consider using `dist.locate_file("")` as a more reliable way to find the package's root location

### Related Files

- Upstream fix in `amplifier-module-resolution` (commit `726288fe`)
- `uv.lock` - Must be upgraded to get the latest version with the fix

### Getting the Fix

The fix is merged in upstream `amplifier-module-resolution`. If you're on an old lock file, run:

```bash
uv lock --upgrade-package amplifier-module-resolution && uv sync
```

This upgrades the locked commit to include the `.dist-info` filtering fix.

---

## Settings Modal - Supporting Multiple Providers (2025-12-04)

### Issue

The Settings modal only showed Anthropic API key and didn't support other providers (OpenAI, Azure OpenAI, Ollama, vLLM).

### Solution

Refactored the credentials system to be list-based and generic:

1. **Backend** (`credentials.py`, `settings.py`):
   - Define all credentials in a central list
   - Generic `GET /settings/credentials` returns array of all credentials with status
   - Generic `PUT/DELETE /credentials/{key}` for any credential

2. **Frontend** (`types.ts`, `api.ts`, `SettingsModal.tsx`):
   - `CredentialsStatus.credentials: CredentialInfo[]`
   - Dynamically render cards for all credentials
   - Configuration for placeholders and help URLs per credential type

### Key Learnings

- List-based APIs are more extensible than object-based APIs when the number of items may grow
- Store credential metadata (display name, env var name, help URL) alongside the credential definition

---

## Settings Modal - Overriding Env Var Credentials (2025-12-04)

### Issue

Users couldn't override a credential that was already configured via environment variable. The input form was hidden when `source === 'env'`.

### Solution

Always show the input form regardless of credential source. The env var note explains the precedence but allows users to store a fallback value.

### Key Learning

Don't hide functionality based on current state - users may want to prepare for different states (e.g., storing a credential as backup even when env var is set).

---

## Agent Delegation Fails with "No module named 'amplifier_app_cli'" (2025-12-05)

### Issue

When using profiles with agent delegation (e.g., `foundation:explorer`), the workbench failed with:

```
Error: Delegation failed: No module named 'amplifier_app_cli'
```

### Root Cause

The upstream `amplifier-module-tool-task` module has hardcoded imports:

```python
# Upstream tool-task (problematic):
from amplifier_app_cli.session_spawner import spawn_sub_session
from amplifier_app_cli.session_spawner import resume_sub_session
```

This couples the tool-task module to the CLI application. The workbench originally didn't install `amplifier_app_cli`, so the import fails at runtime when the task tool tries to delegate to an agent.

### Solution

Added `amplifier-app-cli` as a dependency to satisfy the upstream `tool-task` module's imports:

```toml
# In pyproject.toml dependencies:
"amplifier-app-cli",  # Required for tool-task's session_spawner (until decoupled upstream)

# In [tool.uv.sources]:
amplifier-app-cli = { git = "https://github.com/microsoft/amplifier-app-cli", branch = "main" }
```

This allows the upstream `tool-task` module to import `amplifier_app_cli.session_spawner` successfully.

**Note**: This is a temporary workaround until the upstream `amplifier-module-tool-task` is decoupled from `amplifier-app-cli`. The ideal long-term solution is for upstream to use a capability-based approach.

### Key Learnings

1. **Upstream coupling creates integration challenges** - When modules have hardcoded imports, downstream consumers must satisfy those dependencies.

2. **Local forks create dependency conflicts** - If you have local forks of packages that upstream also depends on, uv won't allow conflicting URLs.

3. **Sometimes the simplest solution wins** - Adding a dependency is cleaner than forking modules, as long as there are no transitive conflicts.

### Related Files

- `pyproject.toml` - Added `amplifier-app-cli` dependency

### Prevention

- When creating portable modules, prefer capability-based interfaces over direct imports
- Test modules in environments without the original host application
- Consider opening upstream PRs to decouple tightly-coupled modules

---

## Agent Discovery Path Mismatch - Internal vs External Collections (2025-12-05)

### Issue

When using profiles with agent delegation (e.g., `developer-expertise:dev`), agents from internal collections like `foundation` and `developer-expertise` were not discovered:

```
Error: Agent 'foundation:explorer' not found
```

Only agents from external collections (installed packages like `design-intelligence`) were found.

### Root Cause

In `src/amplifier_playground/web/routes/sessions.py`, the `build_agent_loader()` function only checked one path for agents:

```python
# Original broken code
for coll in coll_manager.list_collections():
    coll_path = coll_manager.resolve_collection(coll.name)
    if coll_path:
        agents_path = coll_path.parent / "agents"  # Only works for external collections!
        if agents_path.exists():
            search_paths.append(agents_path)
```

The problem: `resolve_collection()` returns different path structures:
- **Internal collections** (bundled in workbench): Return the collection root directory
  - `foundation` → `/path/to/collections/foundation`
  - Agents are at `coll_path / "agents"` → `/path/to/collections/foundation/agents`
- **External collections** (installed packages): Return the Python package directory
  - `design-intelligence` → `/path/to/amplifier-collection-design-intelligence/design_intelligence`
  - Agents are at `coll_path.parent / "agents"` → `/path/to/amplifier-collection-design-intelligence/agents`

### Solution

Check both paths for agents:

```python
# Fixed code
for coll in coll_manager.list_collections():
    coll_path = coll_manager.resolve_collection(coll.name)
    if coll_path:
        # Check both paths - internal collections use coll_path/agents
        direct_agents = coll_path / "agents"
        if direct_agents.exists():
            search_paths.append(direct_agents)
        # External collections use coll_path.parent/agents (package layout)
        parent_agents = coll_path.parent / "agents"
        if parent_agents.exists() and parent_agents != direct_agents:
            search_paths.append(parent_agents)
```

### Key Learnings

1. **Collection path structures differ by type** - Internal (directory-based) vs external (package-based) collections have different layouts
2. **Always check both agent locations** - When discovering agents, check both `coll_path/agents` and `coll_path.parent/agents`
3. **Test with mixed collection sources** - Ensure agent discovery works for both bundled and installed collections

### Related Files

- `src/amplifier_playground/web/routes/sessions.py` - Contains `build_agent_loader()` function
- `src/amplifier_playground/data/collections/*/agents/` - Internal collection agents
- `~/.amplifier/collections/*/agents/` - External collection agents

### Prevention

- When building loaders that need to find assets in collections, consider both internal and external collection layouts
- Test with mixed collection sources (bundled + installed packages)
- Document the expected directory structures for collections
