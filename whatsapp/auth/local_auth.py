"""
LocalAuth — persists session to disk via Playwright's user_data_dir.
Mirrors src/authStrategies/LocalAuth.js
"""
from __future__ import annotations
import os
from pathlib import Path
from .base import BaseAuthStrategy


class LocalAuth(BaseAuthStrategy):
    """
    Saves the WhatsApp Web session to a local directory so that
    subsequent runs skip the QR scan.

    Args:
        client_id: Unique string to differentiate multiple sessions.
        data_path:  Root folder for session data. Default: ./.wwebjs_auth/
    """

    def __init__(self, client_id: str = "", data_path: str = ".wwebjs_auth") -> None:
        super().__init__()
        self.client_id = client_id
        self.data_path = Path(data_path).resolve()
        self.user_data_dir: Path | None = None

    async def before_browser_initialized(self) -> None:
        session_name = f"session-{self.client_id}" if self.client_id else "session"
        self.user_data_dir = self.data_path / session_name
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        # Inject into client's playwright launch options
        if self.client:
            self.client._playwright_opts["user_data_dir"] = str(self.user_data_dir)

    async def logout(self) -> None:
        """Remove the stored session on logout."""
        import shutil
        if self.user_data_dir and self.user_data_dir.exists():
            shutil.rmtree(self.user_data_dir, ignore_errors=True)
