"""
MessageMedia — mirrors src/structures/MessageMedia.js
Holds base64-encoded file data for sending/receiving media.
"""
from __future__ import annotations
import base64
import mimetypes
import os
from pathlib import Path
from typing import Optional

import httpx


class MessageMedia:
    def __init__(
        self,
        mimetype: str,
        data: str,
        filename: Optional[str] = None,
        filesize: Optional[int] = None,
    ) -> None:
        self.mimetype = mimetype
        self.data = data          # base64 string
        self.filename = filename
        self.filesize = filesize

    # ------------------------------------------------------------------ #
    # Factory methods                                                       #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_file(cls, file_path: str) -> "MessageMedia":
        """Create from a local file."""
        path = Path(file_path)
        b64 = base64.b64encode(path.read_bytes()).decode()
        mime, _ = mimetypes.guess_type(file_path)
        mime = mime or "application/octet-stream"
        size = path.stat().st_size
        return cls(mime, b64, path.name, size)

    @classmethod
    async def from_url(
        cls,
        url: str,
        filename: Optional[str] = None,
        unsafe_mime: bool = False,
    ) -> "MessageMedia":
        """Download media from a URL asynchronously."""
        mime, _ = mimetypes.guess_type(url)
        if not mime and not unsafe_mime:
            raise ValueError(
                "Cannot determine MIME type from URL. "
                "Pass unsafe_mime=True to download anyway."
            )
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            r.raise_for_status()
        content_type = r.headers.get("content-type", mime or "application/octet-stream")
        mime = mime or content_type.split(";")[0].strip()
        b64 = base64.b64encode(r.content).decode()
        fname = filename or url.rstrip("/").split("/")[-1] or "file"
        return cls(mime, b64, fname, len(r.content))

    def to_dict(self) -> dict:
        return {
            "mimetype": self.mimetype,
            "data": self.data,
            "filename": self.filename,
            "filesize": self.filesize,
        }

    def __repr__(self) -> str:
        return f"<MessageMedia mimetype={self.mimetype!r} filename={self.filename!r}>"
