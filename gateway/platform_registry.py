"""Platform registry — Hermes-style plugin registry for messaging adapters.

New platforms register themselves at import time; GatewayRunner looks them up
by config name at runtime.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class PlatformEntry:
    """Metadata + factory for a single platform adapter."""

    name: str                      # Config key, e.g. "feishu"
    label: str                     # Human-readable label
    adapter_factory: Callable[[Any], Any]  # config -> BasePlatformAdapter instance
    check_fn: Callable[[], bool] = field(default=lambda: True)  # dependency check
    validate_config: Optional[Callable[[Any], bool]] = None


class PlatformRegistry:
    """Module-level singleton registry for all messaging platforms."""

    def __init__(self) -> None:
        self._entries: Dict[str, PlatformEntry] = {}

    def register(self, entry: PlatformEntry) -> None:
        """Register a new platform adapter."""
        self._entries[entry.name] = entry

    def create_adapter(self, name: str, config: Any) -> Optional[Any]:
        """Instantiate an adapter by registered name, or None if unavailable."""
        entry = self._entries.get(name)
        if entry is None:
            return None
        if not entry.check_fn():
            return None
        if entry.validate_config is not None and not entry.validate_config(config):
            return None
        return entry.adapter_factory(config)

    def list_platforms(self) -> Dict[str, PlatformEntry]:
        """Return a snapshot of all registered entries."""
        return dict(self._entries)


# Module-level singleton — imported by adapters to register, by runner to resolve.
platform_registry = PlatformRegistry()
