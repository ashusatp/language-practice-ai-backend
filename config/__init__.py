from typing import Any
from .config import Config, config, settings

__all__ = ["Config", "config", "settings"]


def __getattr__(name: str) -> Any:
    """Allows accessing attributes directly on the module, e.g. import config; config.livekit_url"""
    if hasattr(config, name):
        return getattr(config, name)
    raise AttributeError(f"module 'config' has no attribute '{name}'")
