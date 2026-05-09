"""Contact structures — mirrors src/structures/Contact.js, BusinessContact.js"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional

from .base import Base

if TYPE_CHECKING:
    from ..client import Client


class Contact(Base):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client)
        self._patch(data)

    def _patch(self, data: dict[str, Any]) -> "Contact":
        self.id = data.get("id", {})
        self.name = data.get("name", "")
        self.short_name = data.get("shortName", "")
        self.pushname = data.get("pushname", "")
        self.number: str = data.get("userid", "")
        self.is_me = data.get("isMe", False)
        self.is_user = data.get("isUser", False)
        self.is_group = data.get("isGroup", False)
        self.is_wa_contact = data.get("isWAContact", False)
        self.is_my_contact = data.get("isMyContact", False)
        self.is_blocked = data.get("isBlocked", False)
        self.is_business = data.get("isBusiness", False)
        self.is_enterprise = data.get("isEnterprise", False)
        self.verified_name = data.get("verifiedName")
        self.status_mute = data.get("statusMute", False)
        self._data = data
        return super()._patch(data)

    async def get_profile_pic_url(self) -> Optional[str]:
        return await self.client.get_profile_pic_url(self.id.get("_serialized", ""))

    async def get_common_groups(self) -> list:
        return await self.client.get_common_groups(self.id.get("_serialized", ""))

    async def block(self) -> bool:
        return bool(await self.client.page.evaluate(
            """async (contactId) => {
                const wid = window.require('WAWebWidFactory').createWid(contactId);
                await window.require('WAWebBlockContactAction').blockContactAction(wid);
                return true;
            }""",
            self.id.get("_serialized"),
        ))

    async def unblock(self) -> bool:
        return bool(await self.client.page.evaluate(
            """async (contactId) => {
                const wid = window.require('WAWebWidFactory').createWid(contactId);
                await window.require('WAWebUnblockContactAction').unblockContactAction(wid);
                return true;
            }""",
            self.id.get("_serialized"),
        ))

    async def get_chat(self):
        return await self.client.get_chat_by_id(self.id.get("_serialized", ""))

    def __repr__(self) -> str:
        return f"<Contact id={self.id.get('_serialized')!r} name={self.name!r}>"


class PrivateContact(Contact):
    pass


class BusinessContact(Contact):
    def __init__(self, client: "Client", data: dict[str, Any]) -> None:
        super().__init__(client, data)
        bp = data.get("businessProfile") or {}
        self.biz_name: str = bp.get("pushname", "")
        self.description: str = bp.get("description", "")
        self.email: str = bp.get("email", "")
        self.website: list[str] = bp.get("website", [])
        self.address: str = bp.get("address", "")
        self.latitude = bp.get("latitude")
        self.longitude = bp.get("longitude")
        self.categories: list[dict] = bp.get("categories", [])

    def __repr__(self) -> str:
        return f"<BusinessContact id={self.id.get('_serialized')!r} name={self.name!r}>"
