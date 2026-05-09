"""Base structure mirroring src/structures/Base.js"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..client import Client


class Base:
    def __init__(self, client: "Client") -> None:
        self.client = client

    def _patch(self, data: dict[str, Any]) -> "Base":
        return self
