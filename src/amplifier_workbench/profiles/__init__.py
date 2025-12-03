"""Profile loading and compilation for Amplifier Workbench."""

from .compiler import compile_profile_to_mount_plan
from .exceptions import (
    ProfileCircularInheritanceError,
    ProfileError,
    ProfileLoadError,
    ProfileNotFoundError,
    ProfileValidationError,
)
from .loader import CollectionResolverProtocol, ProfileLoader
from .schema import AgentsConfig, ModuleConfig, Profile, ProfileMetadata, SessionConfig
from .utils import parse_frontmatter, parse_markdown_body

__all__ = [
    # Schema
    "Profile",
    "ProfileMetadata",
    "ModuleConfig",
    "SessionConfig",
    "AgentsConfig",
    # Loader
    "ProfileLoader",
    "CollectionResolverProtocol",
    # Compiler
    "compile_profile_to_mount_plan",
    # Exceptions
    "ProfileError",
    "ProfileNotFoundError",
    "ProfileValidationError",
    "ProfileLoadError",
    "ProfileCircularInheritanceError",
    # Utils
    "parse_frontmatter",
    "parse_markdown_body",
]
