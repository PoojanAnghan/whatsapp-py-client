"""
Client — the main entry point. Mirrors src/Client.js
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from pyee import EventEmitter as AsyncIOEventEmitter
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from .auth.base import BaseAuthStrategy
from .auth.no_auth import NoAuth
from .constants import Events, Status, WHATS_WEB_URL, DEFAULT_USER_AGENT
from .injected import (
    EXPOSE_AUTH_STORE_JS,
    WIRE_QR_EVENTS_JS,
    WIRE_AUTH_STATE_JS,
    ATTACH_MSG_LISTENERS_JS,
    GET_CLIENT_INFO_JS,
    CHECK_WWEBJS_JS,
    GET_WWEB_VERSION_JS,
    LOAD_UTILS_JS,
)
from .structures.message import Message
from .structures.message_media import MessageMedia
from .structures.misc import (
    ClientInfo, Call, Reaction, PollVote, GroupNotification, Label
)
from .factories import ChatFactory, ContactFactory

logger = logging.getLogger(__name__)


class Client(AsyncIOEventEmitter):
    """
    Python WhatsApp Web client.

    Usage::

        client = Client(auth_strategy=LocalAuth())

        @client.on('qr')
        async def on_qr(qr): print(qr)

        @client.on('message')
        async def on_message(msg):
            if msg.body == '!ping':
                await client.send_message(msg.from_, 'pong')

        asyncio.run(client.initialize())
    """

    def emit(self, event: str, *args, **kwargs):
        """Override to schedule async listeners as asyncio tasks."""
        listeners = self.listeners(event)
        for listener in listeners:
            if asyncio.iscoroutinefunction(listener):
                try:
                    loop = asyncio.get_event_loop()
                    task = loop.create_task(listener(*args, **kwargs))
                    def _done_callback(t: asyncio.Task):
                        try:
                            t.result()
                        except Exception as e:
                            print(f"❌ Error in async listener for {event!r}: {e}")
                            import traceback
                            traceback.print_exc()
                    task.add_done_callback(_done_callback)
                except RuntimeError:
                    pass  # no running loop
            else:
                try:
                    listener(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in listener for {event!r}: {e}")

    def __init__(
        self,
        auth_strategy: Optional[BaseAuthStrategy] = None,
        options: Optional[dict] = None,
    ) -> None:
        super().__init__()
        self.auth_strategy: BaseAuthStrategy = auth_strategy or NoAuth()
        self.auth_strategy.setup(self)
        self.options: dict = options or {}
        self.status = Status.INITIALIZING
        self.info: Optional[ClientInfo] = None

        # Playwright internals
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright_opts: dict = {}   # populated by auth strategy
        self._authenticated: Optional[asyncio.Event] = None  # created lazily in initialize()

    # ================================================================== #
    # Lifecycle                                                            #
    # ================================================================== #

    async def initialize(self) -> None:
        """Launch browser, navigate to WhatsApp Web, inject bridge."""
        # Must be created inside the running event loop
        self._authenticated = asyncio.Event()
        await self.auth_strategy.before_browser_initialized()

        self._playwright = await async_playwright().start()
        pw = self._playwright

        headless = self.options.get("headless", True)
        user_data_dir = self._playwright_opts.get("user_data_dir")

        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ]

        if user_data_dir:
            self._context = await pw.chromium.launch_persistent_context(
                user_data_dir,
                headless=headless,
                args=launch_args,
                user_agent=self.options.get("user_agent", DEFAULT_USER_AGENT),
            )
            self.page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        else:
            self._browser = await pw.chromium.launch(
                headless=headless,
                args=launch_args,
            )
            self._context = await self._browser.new_context(
                user_agent=self.options.get("user_agent", DEFAULT_USER_AGENT),
            )
            self.page = await self._context.new_page()

        # Forward browser console to Python stdout
        self.page.on("console", lambda msg: print(f"[browser] {msg.type}: {msg.text}"))

        await self.auth_strategy.after_browser_initialized()

        # Intercept WA web version if configured
        await self._init_web_version_cache()

        print(f"[WA-PY] Navigating to {WHATS_WEB_URL}...")
        await self.page.goto(WHATS_WEB_URL, wait_until="domcontentloaded")
        print("[WA-PY] Page loaded. Starting injection...")

        # Core injection
        await self._inject()
        print("[WA-PY] Injection complete.")

        # Re-inject on navigation (logout/reload)
        self.page.on("framenavigated", self._on_frame_navigated)

        # Keep running
        await self._authenticated.wait()

    async def _on_frame_navigated(self, frame) -> None:
        if frame == self.page.main_frame:
            await self._inject()

    async def _init_web_version_cache(self) -> None:
        cache_type = self.options.get("web_version_cache", {}).get("type", "none")
        if cache_type == "none":
            return
        # TODO: implement local/remote cache interception via page.route()

    # ================================================================== #
    # Bridge injection                                                     #
    # ================================================================== #

    async def _inject(self) -> None:
        """
        Wire up AuthStore, QR events, state events.
        Mirrors Client.inject() from whatsapp-web.js exactly.
        """
        # Step 1: Wait for WhatsApp Web JS to fully load
        print("[WA-PY] Waiting for WhatsApp Web JS...")
        auth_timeout = self.options.get("auth_timeout_ms", 30_000) / 1000
        deadline = asyncio.get_event_loop().time() + auth_timeout
        while asyncio.get_event_loop().time() < deadline:
            debug_info = await self.page.evaluate("({ exists: window.Debug != undefined, version: window.Debug?.VERSION })")
            print(f"[WA-PY] window.Debug exists: {debug_info['exists']}, version: {debug_info['version']}")
            if debug_info["exists"] and debug_info["version"]:
                print(f"[WA-PY] WhatsApp Web JS loaded. Version: {debug_info['version']}")
                break
            await asyncio.sleep(1.0)
        else:
            raise RuntimeError("WhatsApp Web failed to load (auth timeout)")

        # Step 2: Expose AuthStore on window
        print("[WA-PY] Exposing AuthStore...")
        try:
            await self.page.evaluate(EXPOSE_AUTH_STORE_JS)
            print("[WA-PY] AuthStore exposed.")
        except Exception as e:
            print(f"[WA-PY] AuthStore inject error: {e}")
            return

        # Step 3: Wait for socket state to settle out of transitional states
        print("[WA-PY] Waiting for socket state to settle...")
        need_auth = await self.page.evaluate("""
            async () => {
                let state = window.require('WAWebSocketModel').Socket.state;
                console.log('[WA-PY] Current socket state:', state);
                if (['OPENING', 'UNLAUNCHED', 'PAIRING'].includes(state)) {
                    await new Promise((resolve) => {
                        window.require('WAWebSocketModel').Socket.on(
                            'change:state',
                            function waitTillInit(_appState, s) {
                                console.log('[WA-PY] Socket state changed to:', s);
                                if (!['OPENING', 'UNLAUNCHED', 'PAIRING'].includes(s)) {
                                    window.require('WAWebSocketModel').Socket.off(
                                        'change:state', waitTillInit
                                    );
                                    resolve();
                                }
                            }
                        );
                    });
                }
                state = window.require('WAWebSocketModel').Socket.state;
                return state === 'UNPAIRED' || state === 'UNPAIRED_IDLE';
            }
        """)
        print(f"[WA-PY] Socket settled. Need auth: {need_auth}")

        # Step 4: Expose all Python callbacks
        print("[WA-PY] Exposing Python callbacks...")
        await self._expose("onQRChangedEvent", self._on_qr)
        await self._expose("onAuthAppStateChangedEvent", self._on_auth_state_changed)
        await self._expose("onAppStateHasSyncedEvent", self._on_app_state_synced)
        await self._expose("onOfflineProgressUpdateEvent", self._on_offline_progress)
        await self._expose("onLogoutEvent", self._on_logout)

        # Step 5: If auth needed, build and fire proper compound QR string
        if need_auth:
            print("[WA-PY] Starting QR generation...")
            await self.page.evaluate(WIRE_QR_EVENTS_JS)

        # Step 6: Always wire state/sync/logout events
        print("[WA-PY] Wiring state events...")
        await self.page.evaluate(WIRE_AUTH_STATE_JS)

    async def _expose(self, name: str, callback) -> None:
        try:
            await self.page.expose_function(name, callback)
        except Exception:
            pass  # already exposed on re-inject

    # ================================================================== #
    # Auth event handlers                                                  #
    # ================================================================== #

    async def _on_qr(self, qr: str) -> None:
        self.status = Status.AUTHENTICATING
        self.emit(Events.QR_RECEIVED, qr)

    async def _on_auth_state_changed(self, state: str) -> None:
        self.emit(Events.STATE_CHANGED, state)

    async def _on_offline_progress(self, pct: int) -> None:
        self.emit(Events.LOADING_SCREEN, pct, "Loading messages")

    async def _on_logout(self) -> None:
        self.emit(Events.DISCONNECTED, "LOGOUT")
        await self.auth_strategy.logout()

    async def _on_app_state_synced(self) -> None:
        """Called when WA signals auth is done and data is ready."""
        if getattr(self, "_synced", False):
            return   # already handled
        self._synced = True
        print("[WA-PY] Loading WWebJS utils...")
        try:
            await self.page.evaluate(LOAD_UTILS_JS)
            print("[WA-PY] LOAD_UTILS_JS evaluated OK")
        except Exception as e:
            print(f"[WA-PY] LOAD_UTILS_JS ERROR: {e}")
            return

        # Wait for WWebJS to be available (up to 30s)
        for _ in range(60):
            ready = await self.page.evaluate(CHECK_WWEBJS_JS)
            if ready:
                break
            await asyncio.sleep(0.5)
        else:
            print("[WA-PY] ERROR: WWebJS never became available after injection")
            return

        # Get client info
        info_data = await self.page.evaluate(GET_CLIENT_INFO_JS)
        self.info = ClientInfo(self, info_data)
        self.status = Status.READY

        self.emit(Events.AUTHENTICATED, await self.auth_strategy.get_auth_event_payload())

        # Attach all event listeners
        await self._attach_event_listeners()

        self.emit(Events.READY)
        await self.auth_strategy.after_auth_ready()
        self._authenticated.set()

    async def _attach_event_listeners(self) -> None:
        await self._expose("onAddMessageEvent", self._on_message)
        await self._expose("onAddMessageCiphertextEvent", self._on_message_ciphertext)
        await self._expose("onCiphertextFailedEvent", self._on_ciphertext_failed)
        await self._expose("onChangeMessageEvent", self._on_change_message)
        await self._expose("onChangeMessageTypeEvent", self._on_change_message_type)
        await self._expose("onMessageAckEvent", self._on_message_ack)
        await self._expose("onMessageMediaUploadedEvent", self._on_media_uploaded)
        await self._expose("onRemoveMessageEvent", self._on_remove_message)
        await self._expose("onEditMessageEvent", self._on_edit_message)
        await self._expose("onRemoveChatEvent", self._on_remove_chat)
        await self._expose("onArchiveChatEvent", self._on_archive_chat)
        await self._expose("onChatUnreadCountEvent", self._on_unread_count)
        await self._expose("onAppStateChangedEvent", self._on_app_state_changed)
        await self._expose("onBatteryStateChangedEvent", self._on_battery_changed)
        await self._expose("onIncomingCall", self._on_incoming_call)
        await self._expose("onReaction", self._on_reaction)
        await self._expose("onPollVoteEvent", self._on_poll_vote)
        await self.page.evaluate(ATTACH_MSG_LISTENERS_JS)

    # ================================================================== #
    # Browser event handlers                                               #
    # ================================================================== #

    async def _on_message(self, data: dict) -> None:
        msg = Message(self, data)
        self.emit(Events.MESSAGE_RECEIVED, msg)
        if msg.from_me:
            self.emit(Events.MESSAGE_CREATE, msg)

    async def _on_message_ciphertext(self, data: dict) -> None:
        self.emit(Events.MESSAGE_CIPHERTEXT, Message(self, data))

    async def _on_ciphertext_failed(self, data: dict) -> None:
        self.emit(Events.MESSAGE_CIPHERTEXT_FAILED, Message(self, data))

    async def _on_change_message(self, data: dict) -> None:
        # contact_changed detection
        if data.get("type") == "notification_template" and data.get("subtype") == "contact_to_contact":
            old_id = data.get("templateParams", [None])[0]
            new_id = data.get("templateParams", [None, None])[1]
            self.emit(Events.CONTACT_CHANGED, Message(self, data), old_id, new_id, True)

    async def _on_change_message_type(self, data: dict) -> None:
        if data.get("type") == "revoked":
            self.emit(Events.MESSAGE_REVOKED_EVERYONE, Message(self, data), None)

    async def _on_message_ack(self, data: dict, ack: int) -> None:
        self.emit(Events.MESSAGE_ACK, Message(self, data), ack)

    async def _on_media_uploaded(self, data: dict) -> None:
        self.emit(Events.MEDIA_UPLOADED, Message(self, data))

    async def _on_remove_message(self, data: dict) -> None:
        self.emit(Events.MESSAGE_REVOKED_ME, Message(self, data))

    async def _on_edit_message(self, data: dict, new_body: str, prev_body: str) -> None:
        self.emit(Events.MESSAGE_EDIT, Message(self, data), new_body, prev_body)

    async def _on_remove_chat(self, data: dict) -> None:
        self.emit(Events.CHAT_REMOVED, ChatFactory.create(self, data))

    async def _on_archive_chat(self, data: dict, curr: bool, prev: bool) -> None:
        self.emit(Events.CHAT_ARCHIVED, ChatFactory.create(self, data), curr, prev)

    async def _on_unread_count(self, data: dict) -> None:
        self.emit(Events.UNREAD_COUNT, data)

    async def _on_app_state_changed(self, state: str) -> None:
        self.emit(Events.STATE_CHANGED, state)

    async def _on_battery_changed(self, data: dict) -> None:
        self.emit(Events.BATTERY_CHANGED, data)

    async def _on_incoming_call(self, data: dict) -> None:
        self.emit(Events.INCOMING_CALL, Call(self, data))

    async def _on_reaction(self, reactions: list) -> None:
        for r in reactions:
            self.emit(Events.MESSAGE_REACTION, Reaction(self, r))

    async def _on_poll_vote(self, votes: list) -> None:
        for v in votes:
            self.emit(Events.VOTE_UPDATE, PollVote(self, v))

    # ================================================================== #
    # Public API — Messaging                                               #
    # ================================================================== #

    async def send_message(
        self,
        chat_id: str,
        content: Any,
        options: Optional[dict] = None,
    ) -> Optional[Message]:
        """Send a message. content can be str, MessageMedia, Location, Poll."""
        opts = options or {}

        # Normalize content type
        if isinstance(content, MessageMedia):
            opts["media"] = content.to_dict()
            content = ""  # Body must be a string for media messages
        elif hasattr(content, "to_dict"):
            content = content.to_dict()

        result = await self.page.evaluate(
            """async ([chatId, content, options]) => {
                const chat = await window.WWebJS.getChat(chatId, {getAsModel: false});
                if (!chat) return null;
                const msg = await window.WWebJS.sendMessage(chat, content, options);
                return JSON.parse(JSON.stringify(msg));
            }""",
            [chat_id, content, opts],
        )
        return Message(self, result) if result else None

    async def edit_message(
        self, message_id: str, content: str, options: Optional[dict] = None
    ) -> Optional[Message]:
        """Edit an existing message."""
        result = await self.page.evaluate(
            """async ([msgId, content, options]) => {
                const msg = window.require('WAWebCollections').Msg.get(msgId)
                    || (await window.require('WAWebCollections').Msg.getMessagesById([msgId]))?.messages?.[0];
                if (!msg) return null;
                const edited = await window.WWebJS.editMessage(msg, content, options);
                return JSON.parse(JSON.stringify(edited));
            }""",
            [message_id, content, options or {}],
        )
        return Message(self, result) if result else None

    async def send_reaction(self, message_id: str, emoji: str) -> None:
        await self.page.evaluate(
            """async ([msgId, emoji]) => {
                const msg = window.require('WAWebCollections').Msg.get(msgId)
                    || (await window.require('WAWebCollections').Msg.getMessagesById([msgId]))?.messages?.[0];
                if (msg) await window.require('WAWebSendReactionMsgAction').sendReactionToMsg(msg, emoji);
            }""",
            [message_id, emoji],
        )

    async def send_seen(self, chat_id: str) -> bool:
        return bool(await self.page.evaluate(
            "async (id) => window.WWebJS.sendSeen(id)",
            chat_id,
        ))

    async def search_messages(self, query: str, **kwargs) -> list[Message]:
        msgs = await self.page.evaluate(
            """async ([query, page, count, remote]) => {
                const {messages} = await window.require('WAWebCollections')
                    .Msg.search(query, page, count, remote);
                return messages.map(m => window.WWebJS.getMessageModel(m));
            }""",
            [query, kwargs.get("page"), kwargs.get("limit", 20), kwargs.get("chat_id")],
        )
        return [Message(self, m) for m in (msgs or [])]

    async def get_message_by_id(self, message_id: str) -> Optional[Message]:
        data = await self.page.evaluate(
            """async (msgId) => {
                let msg = window.require('WAWebCollections').Msg.get(msgId);
                if (msg) return window.WWebJS.getMessageModel(msg);
                const res = await window.require('WAWebCollections').Msg.getMessagesById([msgId]);
                msg = res?.messages?.[0];
                return msg ? window.WWebJS.getMessageModel(msg) : null;
            }""",
            message_id,
        )
        return Message(self, data) if data else None

    # ================================================================== #
    # Public API — Chats                                                   #
    # ================================================================== #

    async def get_chats(self) -> list:
        chats = await self.page.evaluate("async () => await window.WWebJS.getChats()")
        return [ChatFactory.create(self, c) for c in (chats or [])]

    async def get_chat_by_id(self, chat_id: str):
        data = await self.page.evaluate(
            "async (id) => await window.WWebJS.getChat(id)",
            chat_id,
        )
        return ChatFactory.create(self, data) if data else None

    async def get_channels(self) -> list:
        channels = await self.page.evaluate("async () => await window.WWebJS.getChannels()")
        return [ChatFactory.create(self, c) for c in (channels or [])]

    async def archive_chat(self, chat_id: str) -> bool:
        return bool(await self.page.evaluate(
            """async (id) => {
                const chat = await window.WWebJS.getChat(id, {getAsModel: false});
                await window.require('WAWebCmd').Cmd.archiveChat(chat, true);
                return true;
            }""",
            chat_id,
        ))

    async def unarchive_chat(self, chat_id: str) -> bool:
        return bool(await self.page.evaluate(
            """async (id) => {
                const chat = await window.WWebJS.getChat(id, {getAsModel: false});
                await window.require('WAWebCmd').Cmd.archiveChat(chat, false);
                return false;
            }""",
            chat_id,
        ))

    async def pin_chat(self, chat_id: str) -> bool:
        return bool(await self.page.evaluate(
            """async (id) => {
                const chat = await window.WWebJS.getChat(id, {getAsModel: false});
                if (chat.pin) return true;
                await window.require('WAWebCmd').Cmd.pinChat(chat, true);
                return true;
            }""",
            chat_id,
        ))

    async def unpin_chat(self, chat_id: str) -> bool:
        return bool(await self.page.evaluate(
            """async (id) => {
                const chat = await window.WWebJS.getChat(id, {getAsModel: false});
                if (!chat.pin) return false;
                await window.require('WAWebCmd').Cmd.pinChat(chat, false);
                return false;
            }""",
            chat_id,
        ))

    async def mute_chat(self, chat_id: str, until=None) -> dict:
        import math
        ts = math.floor(until.timestamp()) if until else -1
        return await self.page.evaluate(
            """async ([id, ts]) => {
                const chat = window.require('WAWebCollections').Chat.get(id)
                    || await window.require('WAWebCollections').Chat.find(id);
                await chat.mute.mute({expiration: ts, sendDevice: true});
                return {isMuted: chat.mute.expiration !== 0, muteExpiration: chat.mute.expiration};
            }""",
            [chat_id, ts],
        )

    async def unmute_chat(self, chat_id: str) -> dict:
        return await self.page.evaluate(
            """async (id) => {
                const chat = window.require('WAWebCollections').Chat.get(id)
                    || await window.require('WAWebCollections').Chat.find(id);
                await chat.mute.unmute({sendDevice: true});
                return {isMuted: false, muteExpiration: 0};
            }""",
            chat_id,
        )

    async def sync_history(self, chat_id: str) -> bool:
        return bool(await self.page.evaluate(
            """async (chatId) => {
                const chatWid = window.require('WAWebWidFactory').createWid(chatId);
                const chat = window.require('WAWebCollections').Chat.get(chatWid)
                    ?? await window.require('WAWebCollections').Chat.find(chatWid);
                if (chat?.endOfHistoryTransferType === 0) {
                    await window.require('WAWebSendNonMessageDataRequest')
                        .sendPeerDataOperationRequest(3, {chatId: chat.id});
                    return true;
                }
                return false;
            }""",
            chat_id,
        ))

    async def get_pinned_messages(self, chat_id: str) -> list[Message]:
        msgs = await self.page.evaluate(
            """async (chatId) => {
                const chatWid = window.require('WAWebWidFactory').createWid(chatId);
                const chat = window.require('WAWebCollections').Chat.get(chatWid)
                    ?? await window.require('WAWebCollections').Chat.find(chatWid);
                if (!chat) return [];
                const pins = await window.require('WAWebPinInChatSchema').getTable()
                    .equals(['chatId'], chatWid.toString());
                const msgs = await Promise.all(
                    pins.filter(p => p.pinType == 1).map(async p => {
                        const r = await window.require('WAWebCollections').Msg
                            .getMessagesById([p.parentMsgKey]);
                        return r?.messages?.[0];
                    })
                );
                return msgs.filter(Boolean).map(m => window.WWebJS.getMessageModel(m));
            }""",
            chat_id,
        )
        return [Message(self, m) for m in (msgs or [])]

    # ================================================================== #
    # Public API — Contacts                                                #
    # ================================================================== #

    async def get_contacts(self) -> list:
        contacts = await self.page.evaluate("() => window.WWebJS.getContacts()")
        return [ContactFactory.create(self, c) for c in (contacts or [])]

    async def get_contact_by_id(self, contact_id: str):
        data = await self.page.evaluate(
            "async (id) => await window.WWebJS.getContact(id)",
            contact_id,
        )
        return ContactFactory.create(self, data) if data else None

    async def get_number_id(self, number: str) -> Optional[dict]:
        if not number.endswith("@c.us"):
            number += "@c.us"
        return await self.page.evaluate(
            """async (number) => {
                const wid = window.require('WAWebWidFactory').createWid(number);
                const result = await window.require('WAWebQueryExistsJob').queryWidExists(wid);
                return result?.wid ?? null;
            }""",
            number,
        )

    async def is_registered_user(self, number: str) -> bool:
        return bool(await self.get_number_id(number))

    async def get_profile_pic_url(self, contact_id: str) -> Optional[str]:
        result = await self.page.evaluate(
            """async (contactId) => {
                try {
                    const chat = await window.WWebJS.getChat(contactId);
                    return await window.require('WAWebContactProfilePicThumbBridge')
                        .requestProfilePicFromServer(chat);
                } catch (e) { return null; }
            }""",
            contact_id,
        )
        return result.get("eurl") if result else None

    async def get_common_groups(self, contact_id: str) -> list:
        return await self.page.evaluate(
            """async (contactId) => {
                let contact = window.require('WAWebCollections').Contact.get(contactId);
                if (!contact) {
                    const wid = window.require('WAWebWidFactory').createWid(contactId);
                    const ctor = window.require('WAWebCollections').Contact.getModelsArray()
                        .find(c => !c.isGroup).constructor;
                    contact = new ctor({id: wid});
                }
                if (contact.commonGroups) return contact.commonGroups.serialize();
                const status = await window.require('WAWebFindCommonGroupsContactAction')
                    .findCommonGroups(contact);
                return status ? contact.commonGroups.serialize() : [];
            }""",
            contact_id,
        )

    # ================================================================== #
    # Public API — Groups                                                  #
    # ================================================================== #

    async def create_group(
        self, title: str, participants: list[str] | None = None, options: dict | None = None
    ) -> dict:
        return await self.page.evaluate(
            """async ([title, participants, options]) => {
                const {messageTimer=0, parentGroupId, autoSendInviteV4=true, comment=''} = options;
                const participantWids = [];
                const failedParticipants = [];
                for (const p of participants) {
                    const pWid = window.require('WAWebWidFactory').createWid(p);
                    if ((await window.require('WAWebQueryExistsJob').queryWidExists(pWid))?.wid)
                        participantWids.push({phoneNumber: pWid});
                    else failedParticipants.push(p);
                }
                const res = await window.require('WAWebGroupCreateJob').createGroup(
                    {title, ephemeralDuration: messageTimer, addressingModeOverride: 'lid'},
                    participantWids
                );
                return {title, gid: res.wid, participants: res.participants};
            }""",
            [title, participants or [], options or {}],
        )

    async def accept_invite(self, invite_code: str) -> str:
        res = await self.page.evaluate(
            "async (code) => await window.require('WAWebGroupInviteJob').joinGroupViaInvite(code)",
            invite_code,
        )
        return res["gid"]["_serialized"]

    async def get_invite_info(self, invite_code: str) -> dict:
        return await self.page.evaluate(
            "async (code) => await window.require('WAWebGroupQueryJob').queryGroupInvite(code)",
            invite_code,
        )

    async def approve_group_membership_requests(self, group_id: str, options: dict | None = None) -> list:
        opts = options or {}
        return await self.page.evaluate(
            "async ([groupId, options]) => window.WWebJS.membershipRequestAction(groupId, 'Approve', options.requesterIds, options.sleep ?? [250,500])",
            [group_id, opts],
        )

    async def reject_group_membership_requests(self, group_id: str, options: dict | None = None) -> list:
        opts = options or {}
        return await self.page.evaluate(
            "async ([groupId, options]) => window.WWebJS.membershipRequestAction(groupId, 'Reject', options.requesterIds, options.sleep ?? [250,500])",
            [group_id, opts],
        )

    # ================================================================== #
    # Public API — Profile & Settings                                      #
    # ================================================================== #

    async def get_wWeb_version(self) -> str:
        return await self.page.evaluate(GET_WWEB_VERSION_JS)

    async def get_state(self) -> str:
        return await self.page.evaluate(
            "() => window.require('WAWebSocketModel').Socket.state ?? null"
        )

    async def set_status(self, status: str) -> None:
        await self.page.evaluate(
            "async (s) => await window.require('WAWebContactStatusBridge').setMyStatus(s)",
            status,
        )

    async def set_display_name(self, name: str) -> bool:
        return bool(await self.page.evaluate(
            """async (name) => {
                if (!window.require('WAWebConnModel').Conn.canSetMyPushname()) return false;
                await window.require('WAWebSetPushnameConnAction').setPushname(name);
                return true;
            }""",
            name,
        ))

    async def set_profile_picture(self, media: MessageMedia) -> bool:
        return bool(await self.page.evaluate(
            "async ([chatId, media]) => window.WWebJS.setPicture(chatId, media)",
            [self.info.wid.get("_serialized") if self.info else "", media.to_dict()],
        ))

    async def reset_state(self) -> None:
        await self.page.evaluate(
            "() => window.require('WAWebSocketModel').Socket.reconnect()"
        )

    # ================================================================== #
    # Public API — Labels                                                  #
    # ================================================================== #

    async def get_labels(self) -> list[Label]:
        labels = await self.page.evaluate("() => window.WWebJS.getLabels()")
        return [Label(self, l) for l in (labels or [])]

    async def get_label_by_id(self, label_id: str) -> Label:
        data = await self.page.evaluate(
            "(id) => window.WWebJS.getLabel(id)", label_id
        )
        return Label(self, data)

    async def get_chat_labels(self, chat_id: str) -> list[Label]:
        labels = await self.page.evaluate(
            "async (id) => await window.WWebJS.getChatLabels(id)", chat_id
        )
        return [Label(self, l) for l in (labels or [])]

    # ================================================================== #
    # Lifecycle — teardown                                                 #
    # ================================================================== #

    async def logout(self) -> None:
        await self.page.evaluate(
            "async () => await window.require('WAWebCmd').Cmd.logout()"
        )
        await self.auth_strategy.logout()

    async def destroy(self) -> None:
        await self.auth_strategy.destroy()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        if self._authenticated:
            self._authenticated.set()  # unblock if still waiting
