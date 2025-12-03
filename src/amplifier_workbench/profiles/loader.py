"""Profile loader for discovering and loading profile files."""

from pathlib import Path

from .exceptions import ProfileError, ProfileNotFoundError
from .schema import Profile
from .utils import parse_frontmatter, parse_markdown_body


class ProfileLoader:
    """Discovers and loads Amplifier profiles from multiple search paths."""

    def __init__(
        self,
        search_paths: list[Path],
        collection_resolver: "CollectionResolverProtocol | None" = None,
    ):
        """
        Initialize profile loader.

        Args:
            search_paths: List of paths to search for profiles
            collection_resolver: Optional collection resolver for collection:profile syntax
        """
        self.search_paths = search_paths
        self.collection_resolver = collection_resolver

    def list_profiles(self) -> list[str]:
        """
        Discover all available profile names.

        Returns:
            List of profile names
        """
        profiles = set()

        for search_path in self.search_paths:
            if not search_path.exists():
                continue

            for profile_file in search_path.glob("*.md"):
                profile_name = profile_file.stem

                # Skip README files
                if profile_name.upper() == "README":
                    continue

                profiles.add(profile_name)

        return sorted(profiles)

    def find_profile_file(self, name: str) -> Path | None:
        """
        Find a profile file by name, checking paths in reverse order (highest precedence first).

        Supports multiple formats:
        1. Collection with simple name: "foundation:base" → searches collection/profiles/base.md
        2. Collection with full path: "foundation:profiles/base.md" → uses exact path
        3. Simple name: "base" → searches local paths

        Args:
            name: Profile name (simple or collection:path format)

        Returns:
            Path to profile file if found, None otherwise
        """
        # Collection syntax (foundation:base or foundation:profiles/base.md)
        if ":" in name:
            if not self.collection_resolver:
                return None

            collection_name, profile_path = name.split(":", 1)
            collection_path = self.collection_resolver.resolve(collection_name)
            if collection_path:
                # Try as full path first
                full_path = collection_path / profile_path
                if full_path.exists() and full_path.is_file():
                    return full_path

                # Try as simple name (foundation:base → profiles/base.md)
                if not profile_path.startswith("profiles/"):
                    simple_name = profile_path if profile_path.endswith(".md") else f"{profile_path}.md"

                    # Check in collection_path/profiles first
                    full_path = collection_path / "profiles" / simple_name
                    if full_path.exists() and full_path.is_file():
                        return full_path

                    # Also check parent/profiles (for collections where resolver returns package dir)
                    full_path = collection_path.parent / "profiles" / simple_name
                    if full_path.exists() and full_path.is_file():
                        return full_path

            return None

        # Simple name: "base" (searches local paths)
        # Search in reverse order (highest precedence first)
        for search_path in reversed(self.search_paths):
            profile_file = search_path / f"{name}.md"
            if profile_file.exists():
                return profile_file

        return None

    def load_profile(self, name: str, _visited: set | None = None) -> Profile:
        """
        Load a profile with inheritance resolution.

        Args:
            name: Profile name (without .md extension)
            _visited: Set of already visited profiles (for circular detection)

        Returns:
            Fully resolved profile

        Raises:
            ProfileNotFoundError: If profile not found
            ProfileError: If circular inheritance or invalid profile
        """
        if _visited is None:
            _visited = set()

        if name in _visited:
            raise ProfileError(f"Circular dependency detected: {' -> '.join(_visited)} -> {name}")

        _visited.add(name)

        profile_file = self.find_profile_file(name)
        if profile_file is None:
            raise ProfileNotFoundError(f"Profile '{name}' not found in search paths")

        try:
            # Read file content
            content = profile_file.read_text()
            data, _ = parse_frontmatter(content)
            markdown_body = parse_markdown_body(content)

            # Add markdown body as system instruction if present
            if markdown_body:
                if "system" not in data:
                    data["system"] = {}
                if "instruction" not in data.get("system", {}):
                    data["system"]["instruction"] = markdown_body

            # Check for inheritance BEFORE validation
            extends = data.get("profile", {}).get("extends")

            if extends:
                # Load parent first
                parent = self.load_profile(extends, _visited)

                # Merge parent into child
                child_dict = data
                parent_dict = parent.model_dump()
                merged_data = self._deep_merge_dicts(parent_dict, child_dict)

                # Now validate the merged profile
                profile = Profile(**merged_data)
            else:
                # No inheritance, validate directly
                profile = Profile(**data)

            # Validate model pair if present
            if hasattr(profile.profile, "model") and profile.profile.model:
                self.validate_model_pair(profile.profile.model)

            return profile

        except ProfileError:
            raise
        except Exception as e:
            raise ProfileError(f"Invalid profile file {profile_file}: {e}") from e

    def validate_model_pair(self, model: str) -> None:
        """
        Validate model is in 'provider/model' format.

        Args:
            model: Model string to validate

        Raises:
            ProfileError: If format is invalid
        """
        if "/" not in model:
            raise ProfileError(f"Model must be 'provider/model' format, got: {model}")

        provider, model_name = model.split("/", 1)
        if not provider or not model_name:
            raise ProfileError(f"Invalid model pair: {model}")

    def _deep_merge_dicts(self, parent: dict, child: dict) -> dict:
        """
        Recursively merge dictionaries.

        Args:
            parent: Parent dictionary
            child: Child dictionary

        Returns:
            Merged dictionary
        """
        result = parent.copy()

        for key, value in child.items():
            if value is None:
                # Explicit None removes inherited value
                result.pop(key, None)
            elif isinstance(value, dict) and key in result and isinstance(result[key], dict):
                # Deep merge nested dicts
                result[key] = self._deep_merge_dicts(result[key], value)
            else:
                # Replace value (including lists)
                result[key] = value

        return result


# Protocol definition for collection resolver
from typing import Protocol


class CollectionResolverProtocol(Protocol):
    """Protocol for resolving collection names to paths."""

    def resolve(self, collection_name: str) -> Path | None:
        """Resolve collection name to filesystem path."""
        ...
