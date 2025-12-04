"""API routes for Amplifier Playground."""

from .collections import router as collections_router
from .configs import router as configs_router
from .modules import router as modules_router
from .profiles import router as profiles_router
from .sessions import router as sessions_router

__all__ = [
    "collections_router",
    "configs_router",
    "modules_router",
    "profiles_router",
    "sessions_router",
]
