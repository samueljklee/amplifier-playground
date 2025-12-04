"""Collection management for Amplifier Playground.

Provides collection discovery and resource loading, wrapping amplifier-collections
with playground-specific search paths.
"""

from pathlib import Path
from typing import Any

from amplifier_collections import CollectionResolver, CollectionResources, discover_collection_resources
from pydantic import BaseModel, Field


class CollectionResolverAdapter:
    """Adapter to make CollectionManager work with ProfileLoader and AgentResolver."""

    def __init__(self, manager: Any):  # CollectionManager, but using Any to avoid forward ref
        self._manager = manager

    def resolve(self, collection_name: str) -> Path | None:
        """Resolve collection name to path."""
        return self._manager.resolve_collection(collection_name)

    def resolve_collection_path(self, collection_name: str) -> Path | None:
        """Alias for resolve() for backward compatibility."""
        return self.resolve(collection_name)


class CollectionInfo(BaseModel):
    """Information about a discovered collection."""

    name: str
    path: Path
    resources: CollectionResources | None = None


class CollectionManager:
    """Manages collections for the playground.

    Provides playground-specific search paths and wraps amplifier-collections
    for discovering and loading collection resources.

    Search path precedence (highest to lowest):
    1. Project-local: ./.amplifier/collections/
    2. User-specific playground: ~/.amplifier-playground/collections/
    3. User-global amplifier: ~/.amplifier/collections/
    """

    def __init__(self, extra_search_paths: list[Path] | None = None):
        """Initialize the collection manager.

        Args:
            extra_search_paths: Additional paths to search for collections.
                               Added at highest precedence.
        """
        self._search_paths = self._build_search_paths(extra_search_paths or [])
        self._resolver = CollectionResolver(self._search_paths)

    def _build_search_paths(self, extra_paths: list[Path]) -> list[Path]:
        """Build search paths list in precedence order (lowest to highest).

        CollectionResolver searches in reverse order, so we put lowest precedence first.

        Search path precedence (highest to lowest):
        1. Extra paths provided by caller
        2. Project-local: ./.amplifier/collections/
        3. User-specific playground: ~/.amplifier-playground/collections/
        4. User-global amplifier: ~/.amplifier/collections/
        5. Bundled collections (package data) - lowest precedence
        """
        paths: list[Path] = []

        # Lowest: Bundled collections (package data)
        package_dir = Path(__file__).parent.parent  # amplifier_playground/
        bundled = package_dir / "data" / "collections"
        if bundled.exists():
            paths.append(bundled)

        # Low: User-global amplifier collections
        user_global = Path.home() / ".amplifier" / "collections"
        if user_global.exists():
            paths.append(user_global)

        # Middle: User-specific playground collections
        user_playground = Path.home() / ".amplifier-playground" / "collections"
        if user_playground.exists():
            paths.append(user_playground)

        # Higher: Project-local collections
        project_local = Path.cwd() / ".amplifier" / "collections"
        if project_local.exists():
            paths.append(project_local)

        # Highest: Extra paths provided by caller
        for p in extra_paths:
            if p.exists():
                paths.append(p)

        return paths

    @property
    def search_paths(self) -> list[Path]:
        """Return the configured search paths."""
        return list(self._search_paths)

    def list_collections(self) -> list[CollectionInfo]:
        """List all available collections.

        Returns:
            List of CollectionInfo with name and path for each discovered collection.
        """
        collections = []
        for name, path in self._resolver.list_collections():
            collections.append(CollectionInfo(name=name, path=path))
        return collections

    def resolve_collection(self, collection_name: str) -> Path | None:
        """Resolve a collection name to its path.

        Args:
            collection_name: Name of the collection to resolve.

        Returns:
            Path to the collection, or None if not found.
        """
        return self._resolver.resolve(collection_name)

    def get_collection_resources(self, collection_name: str) -> CollectionResources | None:
        """Get all resources in a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            CollectionResources with profiles, agents, context, scenario_tools, modules.
            None if collection not found.
        """
        collection_path = self._resolver.resolve(collection_name)
        if collection_path is None:
            return None

        return discover_collection_resources(collection_path)

    def get_collection_info(self, collection_name: str) -> CollectionInfo | None:
        """Get full information about a collection including resources.

        Args:
            collection_name: Name of the collection.

        Returns:
            CollectionInfo with resources populated, or None if not found.
        """
        collection_path = self._resolver.resolve(collection_name)
        if collection_path is None:
            return None

        resources = discover_collection_resources(collection_path)
        return CollectionInfo(name=collection_name, path=collection_path, resources=resources)

    def list_profiles_in_collection(self, collection_name: str) -> list[Path]:
        """List all profile files in a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            List of paths to profile files, empty if collection not found.
        """
        resources = self.get_collection_resources(collection_name)
        if resources is None:
            return []
        return resources.profiles

    def list_agents_in_collection(self, collection_name: str) -> list[Path]:
        """List all agent files in a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            List of paths to agent files, empty if collection not found.
        """
        resources = self.get_collection_resources(collection_name)
        if resources is None:
            return []
        return resources.agents

    def list_modules_in_collection(self, collection_name: str) -> list[Path]:
        """List all module paths in a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            List of paths to modules, empty if collection not found.
        """
        resources = self.get_collection_resources(collection_name)
        if resources is None:
            return []
        return resources.modules
