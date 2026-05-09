"""
RemoteAuth — stores compressed session in a remote store (S3, DB, etc.)
Mirrors src/authStrategies/RemoteAuth.js

Usage:
    class MyStore:
        async def session_exists(self, session: str) -> bool: ...
        async def save(self, session: str, path: str) -> None: ...
        async def extract(self, session: str, path: str) -> None: ...
        async def delete(self, session: str) -> None: ...

    auth = RemoteAuth(store=MyStore(), client_id='bot1', backup_sync_interval_ms=300_000)
"""
from __future__ import annotations
import asyncio
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any, Protocol

from .base import BaseAuthStrategy


class RemoteStore(Protocol):
    async def session_exists(self, session: str) -> bool: ...
    async def save(self, session: str, zip_path: str) -> None: ...
    async def extract(self, session: str, zip_path: str) -> None: ...
    async def delete(self, session: str) -> None: ...


REQUIRED_DIRS = ["Default", "IndexedDB", "Local Storage"]


class RemoteAuth(BaseAuthStrategy):
    def __init__(
        self,
        store: RemoteStore,
        client_id: str = "",
        data_path: str = ".wwebjs_auth",
        backup_sync_interval_ms: int = 300_000,
        rm_max_retries: int = 4,
    ) -> None:
        super().__init__()
        if backup_sync_interval_ms < 60_000:
            raise ValueError("backup_sync_interval_ms must be >= 60000 (1 minute)")
        self.store = store
        self.client_id = client_id
        self.data_path = Path(data_path).resolve()
        self.backup_sync_interval_ms = backup_sync_interval_ms
        self.rm_max_retries = rm_max_retries

        session_name = f"RemoteAuth-{client_id}" if client_id else "RemoteAuth"
        self.session_name = session_name
        self.user_data_dir = self.data_path / session_name
        self.temp_dir = self.data_path / f"wwebjs_temp_session_{client_id}"
        self._backup_task: asyncio.Task | None = None

    async def before_browser_initialized(self) -> None:
        await self._extract_remote_session()
        if self.client:
            self.client._playwright_opts["user_data_dir"] = str(self.user_data_dir)

    async def after_auth_ready(self) -> None:
        if not await self.store.session_exists(self.session_name):
            await asyncio.sleep(60)  # let session stabilize
            await self._store_remote_session(emit=True)
        self._backup_task = asyncio.create_task(self._backup_loop())

    async def _backup_loop(self) -> None:
        while True:
            await asyncio.sleep(self.backup_sync_interval_ms / 1000)
            await self._store_remote_session()

    async def _store_remote_session(self, emit: bool = False) -> None:
        if not self.user_data_dir.exists():
            return
        zip_path = self.data_path / f"{self.session_name}.zip"
        try:
            await asyncio.to_thread(self._compress_session, zip_path)
            await self.store.save(self.session_name, str(zip_path))
            if emit and self.client:
                self.client.emit("remote_session_saved")
        finally:
            for p in [self.temp_dir, zip_path]:
                if Path(p).exists():
                    shutil.rmtree(p, ignore_errors=True)

    def _compress_session(self, zip_path: Path) -> None:
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        stage = self.temp_dir / "Default"
        src = self.user_data_dir / "Default"
        stage.mkdir(parents=True, exist_ok=True)
        for d in REQUIRED_DIRS:
            s = src / d
            if s.exists():
                shutil.copytree(s, stage / d, dirs_exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in self.temp_dir.rglob("*"):
                zf.write(file, file.relative_to(self.temp_dir))

    async def _extract_remote_session(self) -> None:
        if self.user_data_dir.exists():
            shutil.rmtree(self.user_data_dir, ignore_errors=True)
        zip_path = self.data_path / f"{self.session_name}.zip"
        if await self.store.session_exists(self.session_name):
            await self.store.extract(self.session_name, str(zip_path))
            await asyncio.to_thread(self._unzip, zip_path)
        else:
            self.user_data_dir.mkdir(parents=True, exist_ok=True)

    def _unzip(self, zip_path: Path) -> None:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(self.user_data_dir)
        zip_path.unlink(missing_ok=True)

    async def disconnect(self) -> None:
        await self.store.delete(self.session_name)
        if self.user_data_dir.exists():
            shutil.rmtree(self.user_data_dir, ignore_errors=True)
        if self._backup_task:
            self._backup_task.cancel()

    async def logout(self) -> None:
        await self.disconnect()

    async def destroy(self) -> None:
        if self._backup_task:
            self._backup_task.cancel()
