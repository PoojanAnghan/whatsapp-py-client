"""
Base authentication strategy.
Mirrors src/authStrategies/BaseAuthStrategy.js
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..client import Client


class BaseAuthStrategy:
    """
    Lifecycle hooks called by Client during initialization.
    Subclass and override the methods you need.
    """

    def __init__(self) -> None:
        self.client: "Client | None" = None

    def setup(self, client: "Client") -> None:
        """Called by Client.__init__ to bind the client reference."""
        self.client = client

    # ------------------------------------------------------------------ #
    # Lifecycle hooks                                                       #
    # ------------------------------------------------------------------ #

    async def before_browser_initialized(self) -> None:
        """
        Called before the Playwright browser is launched.
        Use to configure launch options (e.g. set user_data_dir).
        """

    async def after_browser_initialized(self) -> None:
        """Called immediately after the browser page is ready."""

    async def on_authentication_needed(self) -> dict[str, Any]:
        """
        Called when WA determines auth is needed (QR scan).
        Return dict with keys:
          failed: bool
          restart: bool
          failure_event_payload: Any
        """
        return {"failed": False, "restart": False, "failure_event_payload": None}

    async def get_auth_event_payload(self) -> Any:
        """Data passed as argument to the 'authenticated' event."""
        return None

    async def after_auth_ready(self) -> None:
        """Called after the client emits 'ready'."""

    async def disconnect(self) -> None:
        """Called when the client disconnects."""

    async def logout(self) -> None:
        """Called when the user logs out."""

    async def destroy(self) -> None:
        """Called when the browser is being closed."""
