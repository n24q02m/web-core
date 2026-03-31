"""Browser provider Protocol for structural typing."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BrowserProvider(Protocol):
    """Interface for stealth browser providers.

    Uses structural typing (Protocol) so providers don't need to inherit.
    """

    @property
    def name(self) -> str: ...

    @property
    def supports_arm64(self) -> bool: ...

    async def launch(self, config: dict[str, Any] | None = None) -> Any:
        """Launch browser and return a context/page object."""
        ...

    async def close(self) -> None:
        """Close browser and release resources."""
        ...
