"""Mention loading for @mention expansion in profiles and agents."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .collection_manager import CollectionManager
from .mentions import has_mentions, parse_mentions

logger = logging.getLogger(__name__)


@dataclass
class ContextMessage:
    """A message containing loaded context from @mentions.

    Compatible with amplifier-profiles MentionLoaderProtocol which
    expects objects with .content attribute (str | list).
    """

    role: str
    content: str


class MentionResolver:
    """Resolves @mentions to file paths.

    Mention types supported:
    1. @collection:path - Collection resources (e.g., @foundation:context/file.md)
    2. @user:path - Shortcut to ~/.amplifier/{path}
    3. @project:path - Shortcut to .amplifier/{path}
    4. @~/path - User home directory
    5. @path - Relative to CWD or relative_to
    """

    def __init__(
        self,
        collection_manager: CollectionManager | None = None,
        project_context_dir: Path | None = None,
        user_context_dir: Path | None = None,
        relative_to: Path | None = None,
    ):
        """Initialize resolver with search paths."""
        self.collection_manager = collection_manager or CollectionManager()
        self.project_context_dir = project_context_dir or (Path.cwd() / ".amplifier" / "context")
        self.user_context_dir = user_context_dir or (Path.home() / ".amplifier" / "context")
        self.relative_to = relative_to

    def resolve(self, mention: str) -> Path | None:
        """Resolve @mention to file path.

        Returns absolute Path if file exists, None if not found.
        """
        # Collection references (@collection:path) and shortcuts (@user:, @project:)
        if ":" in mention[1:] and not mention.startswith("@~/"):
            prefix, path = mention[1:].split(":", 1)

            # Security: Prevent path traversal
            if ".." in path:
                logger.warning(f"Path traversal attempt blocked: {mention}")
                return None

            # @user: shortcut
            if prefix == "user":
                user_path = Path.home() / ".amplifier" / path
                if user_path.exists():
                    return user_path.resolve()
                return None

            # @project: shortcut
            if prefix == "project":
                project_path = Path.cwd() / ".amplifier" / path
                if project_path.exists():
                    return project_path.resolve()
                return None

            # Collection reference
            collection_path = self.collection_manager.resolve_collection(prefix)
            if collection_path:
                # Try at collection path first (package subdirectory)
                resource_path = collection_path / path
                if resource_path.exists():
                    return resource_path.resolve()

                # Hybrid packaging fallback: try parent directory
                if (collection_path / "pyproject.toml").exists():
                    parent_resource_path = collection_path.parent / path
                    if parent_resource_path.exists():
                        return parent_resource_path.resolve()

                logger.debug(f"Collection resource not found: {resource_path}")
                return None

            logger.debug(f"Collection '{prefix}' not found")
            return None

        # @~/ - user home directory
        if mention.startswith("@~/"):
            path_str = mention[3:]
            home_path = Path.home() / path_str
            if home_path.exists():
                return home_path.resolve()
            return None

        # Regular @path - relative to CWD or relative_to
        path_str = mention.lstrip("@")

        if self.relative_to:
            candidate = self.relative_to / path_str
            if candidate.exists():
                return candidate.resolve()

        candidate = Path.cwd() / path_str
        if candidate.exists():
            return candidate.resolve()

        return None


class MentionLoader:
    """Loads files referenced by @mentions.

    Features:
    - Recursive loading (follows @mentions in loaded files)
    - Cycle detection (prevents infinite loops)
    - Silent skip on missing files
    """

    def __init__(self, resolver: MentionResolver | None = None):
        """Initialize loader with optional custom resolver."""
        self.resolver = resolver or MentionResolver()

    def has_mentions(self, text: str) -> bool:
        """Check if text contains @mention patterns."""
        return has_mentions(text)

    def load_mentions(
        self,
        text: str,
        relative_to: Path | None = None,
        deduplicator: Any | None = None,
    ) -> list[ContextMessage]:
        """Load all @mentioned files recursively.

        Args:
            text: Text containing @mentions
            relative_to: Base path for relative mentions
            deduplicator: Ignored (for API compatibility)

        Returns:
            List of ContextMessage objects with role='developer' containing loaded context.
            ContextMessage has .content attribute for compatibility with agent loaders.
        """
        if relative_to is not None:
            self.resolver.relative_to = relative_to

        mentions = parse_mentions(text)
        if not mentions:
            return []

        messages: list[ContextMessage] = []
        visited: set[Path] = set()

        for mention in mentions:
            self._load_recursive(mention, messages, visited)

        return messages

    def _load_recursive(
        self,
        mention: str,
        messages: list[ContextMessage],
        visited: set[Path],
    ) -> None:
        """Recursively load a mention and its dependencies."""
        resolved = self.resolver.resolve(mention)
        if resolved is None:
            logger.debug(f"Skipping unresolved mention: {mention}")
            return

        if resolved in visited:
            logger.debug(f"Skipping already visited: {resolved}")
            return

        visited.add(resolved)

        try:
            content = resolved.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {resolved}: {e}")
            return

        # Check for nested @mentions
        nested_mentions = parse_mentions(content)
        for nested in nested_mentions:
            # Set relative_to for nested mentions
            old_relative = self.resolver.relative_to
            self.resolver.relative_to = resolved.parent
            self._load_recursive(nested, messages, visited)
            self.resolver.relative_to = old_relative

        # Add this content as a developer message (ContextMessage has .content attribute)
        messages.append(ContextMessage(role="developer", content=content))
        logger.debug(f"Loaded mention: {mention} ({len(content)} chars)")
