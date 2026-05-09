"""GroupNotification, ClientInfo, Label, Call, Reaction structures."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

from .base import Base

if TYPE_CHECKING:
    from ..client import Client


class GroupNotification(Base):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client)
        self.id = data.get("id", {})
        self.body = data.get("body", "")
        self.type = data.get("subtype", "")
        self.timestamp = data.get("t", 0)
        raw_remote = data.get("id", {}).get("remote", "")
        self.chat_id = raw_remote.get("_serialized", "") if isinstance(raw_remote, dict) else raw_remote
        raw_author = data.get("author", "")
        self.author = raw_author.get("_serialized", "") if isinstance(raw_author, dict) else raw_author
        self.recipient_ids: list[str] = data.get("recipients", [])

    async def get_chat(self):
        return await self.client.get_chat_by_id(self.chat_id)

    async def get_contact(self):
        return await self.client.get_contact_by_id(self.author)

    async def reply(self, content, options: dict | None = None):
        return await self.client.send_message(self.chat_id, content, options or {})

    def __repr__(self) -> str:
        return f"<GroupNotification type={self.type!r} chat={self.chat_id!r}>"


class ClientInfo(Base):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client)
        self.wid = data.get("wid", {})
        self.pushname: str = data.get("pushname", "")
        self.platform: str = data.get("platform", "")
        self.phone = data.get("phone", {})

    def __repr__(self) -> str:
        return f"<ClientInfo wid={self.wid!r} name={self.pushname!r}>"


class Label(Base):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client)
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.hex_color: str = data.get("hexColor", "")
        self.color: str = data.get("color", "")

    def __repr__(self) -> str:
        return f"<Label id={self.id!r} name={self.name!r}>"


class Call(Base):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client)
        self.id: str = data.get("id", "")
        self.from_: str = data.get("peerJid", "")
        self.is_video: bool = bool(data.get("isVideo"))
        self.is_group: bool = bool(data.get("isGroup"))
        self.from_me: bool = bool(data.get("outgoing"))
        self.timestamp = data.get("t")

    async def reject(self) -> None:
        await self.client.page.evaluate(
            "async ([peerJid, id]) => window.WWebJS.rejectCall(peerJid, id)",
            [self.from_, self.id],
        )

    def __repr__(self) -> str:
        return f"<Call id={self.id!r} from={self.from_!r} video={self.is_video}>"


class Reaction(Base):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client)
        self.id = data.get("msgKey", {})
        self.orphan = data.get("orphan", 0)
        self.orphan_reason = data.get("orphanReason")
        self.timestamp = data.get("timestamp", 0)
        self.reaction: str = data.get("reactionText", "")
        self.read = bool(data.get("read"))
        self.msg_id = data.get("parentMsgKey", {})
        self.sender_id: str = data.get("senderUserJid", "")

    def __repr__(self) -> str:
        return f"<Reaction emoji={self.reaction!r} from={self.sender_id!r}>"


class PollVote(Base):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client)
        self.selected_options: list[int] = data.get("selectedOptionLocalIds", [])
        self.timestamp = data.get("timestamp", 0)
        self.voter_id: str = data.get("senderUserJid", "")
        self.parent_message = data.get("parentMessage")
