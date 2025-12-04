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

- `modules/amplifier-module-resolution/src/amplifier_module_resolution/sources.py` - Contains the fix
- `pyproject.toml` - Updated to use local `amplifier-module-resolution` during development

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
