"""
Injected JS strings.
These are evaluated inside the browser page via page.evaluate().
Content mirrors src/util/Injected/AuthStore/AuthStore.js
"""

EXPOSE_AUTH_STORE_JS = """
(function() {
    window.AuthStore = {};
    window.AuthStore.AppState = window.require('WAWebSocketModel').Socket;
    window.AuthStore.Cmd = window.require('WAWebCmd').Cmd;
    window.AuthStore.Conn = window.require('WAWebConnModel').Conn;
    window.AuthStore.OfflineMessageHandler = window.require('WAWebOfflineHandler').OfflineMessageHandler;
    window.AuthStore.PairingCodeLinkUtils = window.require('WAWebAltDeviceLinkingApi');
    window.AuthStore.Base64Tools = window.require('WABase64');
    window.AuthStore.RegistrationUtils = {
        ...window.require('WAWebCompanionRegClientUtils'),
        ...window.require('WAWebAdvSignatureApi'),
        ...window.require('WAWebUserPrefsInfoStore'),
        ...window.require('WAWebSignalStoreApi'),
    };
})();
"""

WIRE_QR_EVENTS_JS = """
(async function() {
    const registrationInfo =
        await window.AuthStore.RegistrationUtils.waSignalStore.getRegistrationInfo();
    const noiseKeyPair =
        await window.AuthStore.RegistrationUtils.waNoiseInfo.get();

    const staticKeyB64 = window.AuthStore.Base64Tools.encodeB64(
        noiseKeyPair.staticKeyPair.pubKey
    );
    const identityKeyB64 = window.AuthStore.Base64Tools.encodeB64(
        registrationInfo.identityKeyPair.pubKey
    );
    const advSecretKey = window.require('WAWebUserPrefsMultiDevice').getADVSecretKey();
    const platform    = window.AuthStore.RegistrationUtils.DEVICE_PLATFORM;

    const getQR = (ref) =>
        ref + ',' + staticKeyB64 + ',' + identityKeyB64 + ',' + advSecretKey + ',' + platform;

    // Fire immediately if a ref is already set
    if (window.AuthStore.Conn.ref) {
        window.onQRChangedEvent(getQR(window.AuthStore.Conn.ref));
    }
    // Keep firing on every QR refresh
    window.AuthStore.Conn.on('change:ref', (_, ref) => {
        window.onQRChangedEvent(getQR(ref));
    });
})();
"""

WIRE_AUTH_STATE_JS = """
(function() {
    const Socket = window.require('WAWebSocketModel').Socket;
    const Cmd    = window.require('WAWebCmd').Cmd;

    Socket.on('change:state', (_, state) => {
        console.log('[WA-PY] Socket state:', state);
        window.onAuthAppStateChangedEvent(state);
        if (state === 'UNPAIRED_IDLE') {
            Cmd.refreshQR();
        }
    });

    Socket.on('change:hasSynced', () => {
        console.log('[WA-PY] hasSynced fired');
        window.onAppStateHasSyncedEvent();
    });

    // Fire immediately if already synced (race-condition guard)
    if (Socket.hasSynced) {
        console.log('[WA-PY] Already synced on inject — firing now');
        window.onAppStateHasSyncedEvent();
    }

    Cmd.on('offline_progress_update_from_bridge', () => {
        const pct = window.AuthStore.OfflineMessageHandler.getOfflineDeliveryProgress();
        window.onOfflineProgressUpdateEvent(pct);
    });
    Cmd.on('logout', async () => { await window.onLogoutEvent(); });
    Cmd.on('logout_from_bridge', async () => { await window.onLogoutEvent(); });
})();
"""

ATTACH_MSG_LISTENERS_JS = """
(function() {
    const { Msg, Chat } = window.require('WAWebCollections');
    const AppState = window.require('WAWebSocketModel').Socket;

    // Enable placeholder resend for ciphertext recovery
    try {
        const gu = window.require('WAWebSyncGatingUtils');
        gu.isPlaceholderMessageResendEnabled = () => true;
    } catch(e) {}

    Msg.on('add', (msg) => {
        if (!msg.isNewMsg) return;
        if (msg.type !== 'ciphertext') {
            window.onAddMessageEvent(JSON.parse(JSON.stringify(window.WWebJS.getMessageModel(msg))));
            return;
        }
        window.onAddMessageCiphertextEvent(JSON.parse(JSON.stringify(window.WWebJS.getMessageModel(msg))));
        const failTimer = setTimeout(() => {
            if (msg.type !== 'ciphertext') return;
            window.onCiphertextFailedEvent(JSON.parse(JSON.stringify(window.WWebJS.getMessageModel(msg))));
        }, 15000);
        msg.once('change:type', (_msg) => {
            clearTimeout(failTimer);
            if (_msg.type === 'revoked') return;
            window.onAddMessageEvent(JSON.parse(JSON.stringify(window.WWebJS.getMessageModel(_msg))));
        });
    });

    Msg.on('change', (msg) => {
        window.onChangeMessageEvent(JSON.parse(JSON.stringify(window.WWebJS.getMessageModel(msg))));
    });
    Msg.on('change:type', (msg) => {
        window.onChangeMessageTypeEvent(JSON.parse(JSON.stringify(window.WWebJS.getMessageModel(msg))));
    });
    Msg.on('change:ack', (msg, ack) => {
        window.onMessageAckEvent(JSON.parse(JSON.stringify(window.WWebJS.getMessageModel(msg))), ack);
    });
    Msg.on('change:isUnsentMedia', (msg, unsent) => {
        if (msg.id.fromMe && !unsent)
            window.onMessageMediaUploadedEvent(JSON.parse(JSON.stringify(window.WWebJS.getMessageModel(msg))));
    });
    Msg.on('remove', (msg) => {
        if (msg.isNewMsg) window.onRemoveMessageEvent(JSON.parse(JSON.stringify(window.WWebJS.getMessageModel(msg))));
    });
    Msg.on('change:body change:caption', (msg, newBody, prevBody) => {
        window.onEditMessageEvent(JSON.parse(JSON.stringify(window.WWebJS.getMessageModel(msg))), newBody, prevBody);
    });

    AppState.on('change:state', (_, state) => {
        window.onAppStateChangedEvent(state);
    });

    window.require('WAWebConnModel').Conn.on('change:battery', (state) => {
        window.onBatteryStateChangedEvent(state);
    });

    Chat.on('remove', async (chat) => {
        window.onRemoveChatEvent(JSON.parse(JSON.stringify(await window.WWebJS.getChatModel(chat))));
    });
    Chat.on('change:archive', async (chat, curr, prev) => {
        window.onArchiveChatEvent(JSON.parse(JSON.stringify(await window.WWebJS.getChatModel(chat))), curr, prev);
    });
    Chat.on('change:unreadCount', async (chat) => {
        const model = await window.WWebJS.getChatModel(chat);
        window.onChatUnreadCountEvent(JSON.parse(JSON.stringify(model)));
    });

    // Reaction hook via injectToFunction
    window.WWebJS.injectToFunction(
        { module: 'WAWebAddonReactionTableMode', function: 'reactionTableMode.bulkUpsert' },
        (module, origFn, ...args) => {
            window.onReaction(JSON.parse(JSON.stringify(args[0].map((reaction) => ({
                ...reaction,
                msgKey: reaction.id,
                parentMsgKey: reaction.reactionParentKey,
                senderUserJid: (reaction.author ?? reaction.from)._serialized,
                timestamp: reaction.reactionTimestamp / 1000,
            })))));
            return origFn.apply(module, args);
        }
    );

    // Poll vote hook
    window.WWebJS.injectToFunction(
        { module: 'WAWebAddonPollVoteTableMode', function: 'pollVoteTableMode.bulkUpsert' },
        async (module, origFn, ...args) => {
            const votes = await Promise.all(args[0].map(async (vote) => {
                const parentMsgKey = vote.pollUpdateParentKey;
                let parentMessage = Msg.get(parentMsgKey._serialized);
                if (!parentMessage) {
                    const fetched = await Msg.getMessagesById([parentMsgKey._serialized]);
                    parentMessage = fetched?.messages?.[0] || null;
                }
                return {
                    ...vote,
                    msgKey: vote.id,
                    parentMsgKey,
                    senderUserJid: (vote.author ?? vote.from)._serialized,
                    timestamp: vote.t / 1000,
                    sender: vote.author ?? vote.from,
                    parentMessage,
                };
            }));
            window.onPollVoteEvent(JSON.parse(JSON.stringify(votes)));
            return origFn.apply(module, args);
        }
    );

    // Incoming call hook
    try {
        const WAWebCallCollection = window.require('WAWebCallCollection');
        if (WAWebCallCollection && typeof WAWebCallCollection.on === 'function') {
            const mapKey = Object.keys(WAWebCallCollection).find(
                k => WAWebCallCollection[k] instanceof Map
            );
            const callMap = WAWebCallCollection[mapKey];
            const origSet = callMap.set.bind(callMap);
            callMap.set = function(key, value) {
                window.onIncomingCall({
                    id: value.id,
                    peerJid: value.peerJid,
                    isVideo: value.isVideo,
                    isGroup: value.isGroup,
                    canHandleLocally: value.canHandleLocally,
                    outgoing: value.outgoing,
                    webClientShouldHandle: value.webClientShouldHandle,
                    participants: value.participants,
                });
                return origSet(key, value);
            };
        }
    } catch(e) {}
})();
"""

GET_CLIENT_INFO_JS = """
(function() {
    return {
        ...window.require('WAWebConnModel').Conn.serialize(),
        wid: window.require('WAWebUserPrefsMeUser').getMaybeMePnUser()
          || window.require('WAWebUserPrefsMeUser').getMaybeMeLidUser(),
    };
})()
"""

CHECK_WWEBJS_JS = "typeof window.WWebJS !== 'undefined'"
GET_WWEB_VERSION_JS = "window.Debug.VERSION"
