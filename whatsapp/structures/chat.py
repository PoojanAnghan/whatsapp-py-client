"""
Chat structures — mirrors src/structures/Chat.js, GroupChat.js, PrivateChat.js, Channel.js
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional

from .base import Base

if TYPE_CHECKING:
    from ..client import Client
    from .message import Message
    from .message_media import MessageMedia


class Chat(Base):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client)
        self._patch(data)

    def _patch(self, data: dict[str, Any]) -> "Chat":
        self.id = data.get("id", {})
        self.name = data.get("name", "")
        self.is_group = data.get("isGroup", False)
        self.is_channel = data.get("isChannel", False)
        self.is_muted = data.get("isMuted", False)
        self.is_read_only = data.get("isReadOnly", False)
        self.unread_count: int = data.get("unreadCount", 0)
        self.timestamp: int = data.get("t", 0)
        self.archived = data.get("archive", False)
        self.pinned = bool(data.get("pin"))
        self.mute_expiration: int = data.get("muteExpiration", 0)
        self.last_message = data.get("lastMessage")
        self._data = data
        return super()._patch(data)

    # ------------------------------------------------------------------ #
    # Actions                                                              #
    # ------------------------------------------------------------------ #

    async def send_message(self, content, options: dict | None = None):
        return await self.client.send_message(
            self.id.get("_serialized", ""), content, options
        )

    async def send_seen(self) -> bool:
        return await self.client.send_seen(self.id.get("_serialized", ""))

    async def send_state_typing(self) -> None:
        await self.client.page.evaluate(
            "async (id) => window.WWebJS.sendChatstate('typing', id)",
            self.id.get("_serialized"),
        )

    async def send_state_recording(self) -> None:
        await self.client.page.evaluate(
            "async (id) => window.WWebJS.sendChatstate('recording', id)",
            self.id.get("_serialized"),
        )

    async def clear_state(self) -> None:
        await self.client.page.evaluate(
            "async (id) => window.WWebJS.sendChatstate('stop', id)",
            self.id.get("_serialized"),
        )

    async def archive(self) -> bool:
        return await self.client.archive_chat(self.id.get("_serialized", ""))

    async def unarchive(self) -> bool:
        return await self.client.unarchive_chat(self.id.get("_serialized", ""))

    async def pin(self) -> bool:
        return await self.client.pin_chat(self.id.get("_serialized", ""))

    async def unpin(self) -> bool:
        return await self.client.unpin_chat(self.id.get("_serialized", ""))

    async def mute(self, until=None) -> dict:
        return await self.client.mute_chat(self.id.get("_serialized", ""), until)

    async def unmute(self) -> dict:
        return await self.client.unmute_chat(self.id.get("_serialized", ""))

    async def clear_messages(self) -> bool:
        return bool(await self.client.page.evaluate(
            "async (id) => window.WWebJS.sendClearChat(id)",
            self.id.get("_serialized"),
        ))

    async def delete(self) -> bool:
        return bool(await self.client.page.evaluate(
            "async (id) => window.WWebJS.sendDeleteChat(id)",
            self.id.get("_serialized"),
        ))

    async def fetch_messages(self, limit: int = 50) -> list:
        from .message import Message
        msgs = await self.client.page.evaluate(
            """async ([chatId, limit]) => {
                const chat = await window.WWebJS.getChat(chatId, {getAsModel: false});
                if (!chat) return [];
                const msgs = await window.require('WAWebCollections')
                    .Msg.getMessagesById(chat.msgs.map(m => m.id._serialized).slice(-limit));
                return (msgs?.messages || []).map(m => window.WWebJS.getMessageModel(m));
            }""",
            [self.id.get("_serialized"), limit],
        )
        return [Message(self.client, m) for m in (msgs or [])]

    async def sync_history(self) -> bool:
        return await self.client.sync_history(self.id.get("_serialized", ""))

    async def get_labels(self) -> list:
        return await self.client.get_chat_labels(self.id.get("_serialized", ""))

    def __repr__(self) -> str:
        return f"<Chat id={self.id.get('_serialized')!r} name={self.name!r}>"


class PrivateChat(Chat):
    pass


class GroupChat(Chat):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client, data)
        gm = data.get("groupMetadata") or {}
        self.description: str = gm.get("desc", "")
        self.created_at = gm.get("creation")
        self.owner = gm.get("owner")
        self.participants: list[dict] = gm.get("participants", [])
        self.is_announce: bool = bool(gm.get("announce"))
        self.is_restrict: bool = bool(gm.get("restrict"))

    async def add_participants(self, ids: list[str]) -> dict:
        return await self.client.page.evaluate(
            """async ([groupId, ids]) => {
                const result = {};
                for (const id of ids) {
                    const pWid = window.require('WAWebWidFactory').createWid(id);
                    const r = await window.WWebJS.getAddParticipantsRpcResult(
                        window.require('WAWebWidFactory').createWid(groupId), pWid
                    );
                    result[id] = r;
                }
                return result;
            }""",
            [self.id.get("_serialized"), ids],
        )

    async def remove_participants(self, ids: list[str]) -> dict:
        return await self.client.page.evaluate(
            """async ([groupId, ids]) => {
                const groupWid = window.require('WAWebWidFactory').createWid(groupId);
                const group = window.require('WAWebCollections').Chat.get(groupWid)
                    || await window.require('WAWebCollections').Chat.find(groupWid);
                const results = {};
                for (const id of ids) {
                    const pWid = window.require('WAWebWidFactory').createWid(id);
                    await window.require('WAWebGroupParticipantsJob').removeParticipants(group, [pWid]);
                    results[id] = { code: 200 };
                }
                return results;
            }""",
            [self.id.get("_serialized"), ids],
        )

    async def promote_participants(self, ids: list[str]) -> dict:
        return await self.client.page.evaluate(
            """async ([groupId, ids]) => {
                const groupWid = window.require('WAWebWidFactory').createWid(groupId);
                const group = window.require('WAWebCollections').Chat.get(groupWid)
                    || await window.require('WAWebCollections').Chat.find(groupWid);
                for (const id of ids) {
                    const pWid = window.require('WAWebWidFactory').createWid(id);
                    await window.require('WAWebGroupParticipantsJob').promoteParticipants(group, [pWid]);
                }
                return {};
            }""",
            [self.id.get("_serialized"), ids],
        )

    async def demote_participants(self, ids: list[str]) -> dict:
        return await self.client.page.evaluate(
            """async ([groupId, ids]) => {
                const groupWid = window.require('WAWebWidFactory').createWid(groupId);
                const group = window.require('WAWebCollections').Chat.get(groupWid)
                    || await window.require('WAWebCollections').Chat.find(groupWid);
                for (const id of ids) {
                    const pWid = window.require('WAWebWidFactory').createWid(id);
                    await window.require('WAWebGroupParticipantsJob').demoteParticipants(group, [pWid]);
                }
                return {};
            }""",
            [self.id.get("_serialized"), ids],
        )

    async def set_subject(self, subject: str) -> bool:
        return bool(await self.client.page.evaluate(
            """async ([groupId, subject]) => {
                const groupWid = window.require('WAWebWidFactory').createWid(groupId);
                const group = window.require('WAWebCollections').Chat.get(groupWid)
                    || await window.require('WAWebCollections').Chat.find(groupWid);
                await window.require('WAWebGroupMetadataAction').setGroupSubject(group, subject);
                return true;
            }""",
            [self.id.get("_serialized"), subject],
        ))

    async def set_description(self, desc: str) -> bool:
        return bool(await self.client.page.evaluate(
            """async ([groupId, desc]) => {
                const groupWid = window.require('WAWebWidFactory').createWid(groupId);
                const group = window.require('WAWebCollections').Chat.get(groupWid)
                    || await window.require('WAWebCollections').Chat.find(groupWid);
                await window.require('WAWebGroupMetadataAction').setGroupDescription(group, desc, null);
                return true;
            }""",
            [self.id.get("_serialized"), desc],
        ))

    async def leave(self) -> None:
        await self.client.page.evaluate(
            """async (groupId) => {
                const groupWid = window.require('WAWebWidFactory').createWid(groupId);
                const group = window.require('WAWebCollections').Chat.get(groupWid)
                    || await window.require('WAWebCollections').Chat.find(groupWid);
                await window.require('WAWebGroupLeaveJob').leaveGroup(group);
            }""",
            self.id.get("_serialized"),
        )

    async def get_invite_code(self) -> str:
        return await self.client.page.evaluate(
            """async (groupId) => {
                const groupWid = window.require('WAWebWidFactory').createWid(groupId);
                const code = await window.require('WAWebGroupInviteJob').queryGroupInviteCode(groupWid);
                return code;
            }""",
            self.id.get("_serialized"),
        )

    async def revoke_invite(self) -> str:
        return await self.client.page.evaluate(
            """async (groupId) => {
                const groupWid = window.require('WAWebWidFactory').createWid(groupId);
                return await window.require('WAWebGroupRevokeInviteJob').revokeGroupInviteCode(groupWid);
            }""",
            self.id.get("_serialized"),
        )

    async def approve_membership_requests(self, options: dict | None = None) -> list:
        return await self.client.approve_group_membership_requests(
            self.id.get("_serialized", ""), options or {}
        )

    async def reject_membership_requests(self, options: dict | None = None) -> list:
        return await self.client.reject_group_membership_requests(
            self.id.get("_serialized", ""), options or {}
        )

    def __repr__(self) -> str:
        return f"<GroupChat id={self.id.get('_serialized')!r} name={self.name!r} participants={len(self.participants)}>"


class Channel(Chat):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client, data)
        cm = data.get("channelMetadata") or {}
        self.description: str = cm.get("description", "")
        self.invite_link: str = cm.get("inviteLink", "")
        self.subscribers_count: int = cm.get("subscribersCount", 0)
        self.is_verified: bool = bool(cm.get("isVerified"))

    def __repr__(self) -> str:
        return f"<Channel id={self.id.get('_serialized')!r} name={self.name!r}>"
