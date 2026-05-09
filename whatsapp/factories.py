"""
Factory classes — mirrors src/factories/ChatFactory.js and ContactFactory.js
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import Client


class ChatFactory:
    @staticmethod
    def create(client: "Client", data: dict[str, Any]):
        from .structures.chat import PrivateChat, GroupChat, Channel
        if data.get("isChannel"):
            return Channel(client, data)
        if data.get("isGroup"):
            return GroupChat(client, data)
        return PrivateChat(client, data)


class ContactFactory:
    @staticmethod
    def create(client: "Client", data: dict[str, Any]):
        from .structures.contact import PrivateContact, BusinessContact
        if data.get("isBusiness") or data.get("isEnterprise"):
            return BusinessContact(client, data)
        return PrivateContact(client, data)
