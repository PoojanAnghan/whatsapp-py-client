"""
Message structure — mirrors src/structures/Message.js
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional

from .base import Base
from .message_media import MessageMedia

if TYPE_CHECKING:
    from ..client import Client


class Message(Base):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client)
        self._patch(data)

    def _patch(self, data: dict[str, Any]) -> "Message":
        self.id = data.get("id", {})
        self.body = data.get("body", "")
        self.type = data.get("type", "chat")
        self.timestamp = data.get("t", 0)
        # Extract IDs as strings (_serialized)
        from_id = data.get("from")
        self.from_ = from_id.get("_serialized") if isinstance(from_id, dict) else from_id
        
        to_id = data.get("to")
        self.to = to_id.get("_serialized") if isinstance(to_id, dict) else to_id
        self.author = data.get("author")
        self.from_me = data.get("id", {}).get("fromMe", False)
        self.has_media = bool(data.get("hasMedia"))
        self.has_quoted_msg = bool(data.get("hasQuotedMsg"))
        self.has_reaction = bool(data.get("hasReaction"))
        self.mentioned_ids: list[str] = data.get("mentionedJidList", [])
        self.group_mentions: list[dict] = data.get("groupMentions", [])
        self.links: list[dict] = data.get("links", [])
        self.is_forwarded = bool(data.get("isForwarded"))
        self.forwarding_score: int = data.get("forwardingScore", 0)
        self.is_ephemeral = bool(data.get("isEphemeral"))
        self.is_status = bool(data.get("isStatusV3"))
        self.is_starred = bool(data.get("star"))
        self.broadcast = bool(data.get("broadcast"))
        self.duration = data.get("duration")
        self.location = data.get("location")
        self.v_cards: list[str] = data.get("vcardList", [])
        self.invite_v4 = data.get("inviteV4")
        self.media_key = data.get("mediaKey")
        self.media_key_timestamp = data.get("mediaKeyTimestamp")
        self.caption = data.get("caption")
        self.is_gif = bool(data.get("isGif"))
        self.poll_name = data.get("pollName")
        self.poll_options = data.get("pollOptions", [])
        self.protocol_message_key = data.get("protocolMessageKey")
        self._data = data
        return super()._patch(data)

    # ------------------------------------------------------------------ #
    # Actions                                                              #
    # ------------------------------------------------------------------ #

    async def reply(self, content, options: dict | None = None) -> "Message":
        """Reply to this message in the same chat."""
        opts = options or {}
        opts["quoted_message_id"] = self.id.get("_serialized")
        chat_id = self.id.get("remote") if not self.from_me else self.to
        return await self.client.send_message(chat_id, content, opts)

    async def react(self, emoji: str) -> None:
        """React to this message with an emoji. Pass '' to remove."""
        await self.client.send_reaction(self.id.get("_serialized", ""), emoji)

    async def edit(self, content: str, options: dict | None = None) -> "Message":
        """Edit this message."""
        return await self.client.edit_message(self.id.get("_serialized", ""), content, options)

    async def download_media(self) -> Optional[MessageMedia]:
        """Download the media attached to this message."""
        if not self.has_media:
            return None
        result = await self.client.page.evaluate(
            """async (msgId) => {
                const msg = window.require('WAWebCollections').Msg.get(msgId)
                    || (await window.require('WAWebCollections').Msg.getMessagesById([msgId]))?.messages?.[0];
                if (!msg || !msg.hasMedia) return null;
                const data = await window.require('WAWebDownloadManager').downloadAndMaybeDecrypt({
                    directPath: msg.directPath,
                    encFilehash: msg.encFilehash,
                    filehash: msg.filehash,
                    mediaKey: msg.mediaKey,
                    mediaKeyTimestamp: msg.mediaKeyTimestamp,
                    type: msg.type,
                    signal: (new AbortController()).signal,
                });
                const dataUrl = await new Promise(resolve => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.readAsDataURL(data);
                });
                const [mimeData, b64] = dataUrl.split(',');
                const mime = mimeData.split(':')[1].split(';')[0];
                return { mimetype: mime, data: b64, filename: msg.filename };
            }""",
            self.id.get("_serialized"),
        )
        if not result:
            return None
        return MessageMedia(result["mimetype"], result["data"], result.get("filename"))

    async def get_quoted_message(self) -> Optional["Message"]:
        if not self.has_quoted_msg:
            return None
        result = await self.client.page.evaluate(
            """async (msgId) => {
                const msg = window.require('WAWebCollections').Msg.get(msgId)
                    || (await window.require('WAWebCollections').Msg.getMessagesById([msgId]))?.messages?.[0];
                if (!msg || !msg.quotedMsg) return null;
                return window.WWebJS.getMessageModel(msg.quotedMsg);
            }""",
            self.id.get("_serialized"),
        )
        return Message(self.client, result) if result else None

    async def delete(self, everyone: bool = False) -> None:
        await self.client.page.evaluate(
            """async (msgId, everyone) => {
                const msg = window.require('WAWebCollections').Msg.get(msgId)
                    || (await window.require('WAWebCollections').Msg.getMessagesById([msgId]))?.messages?.[0];
                if (msg) await window.require('WAWebDeleteMsgAction').deleteMsgAction(msg, everyone);
            }""",
            self.id.get("_serialized"),
            everyone,
        )

    async def forward(self, chat_id: str) -> None:
        await self.client.page.evaluate(
            "async ([chatId, msgId]) => window.WWebJS.forwardMessage(chatId, msgId)",
            [chat_id, self.id.get("_serialized")],
        )

    async def pin(self, duration: int) -> bool:
        result = await self.client.page.evaluate(
            "async ([msgId, dur]) => window.WWebJS.pinUnpinMsgAction(msgId, 'pin', dur)",
            [self.id.get("_serialized"), duration],
        )
        return bool(result)

    async def unpin(self) -> bool:
        result = await self.client.page.evaluate(
            "async ([msgId]) => window.WWebJS.pinUnpinMsgAction(msgId, 'unpin', 0)",
            [self.id.get("_serialized")],
        )
        return bool(result)

    async def get_chat(self):
        return await self.client.get_chat_by_id(
            self.id.get("remote") if not self.from_me else self.to
        )

    def __repr__(self) -> str:
        return f"<Message id={self.id.get('_serialized')!r} type={self.type!r}>"
