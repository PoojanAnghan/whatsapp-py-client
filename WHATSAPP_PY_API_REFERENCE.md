# WhatsApp-Py Exhaustive API Reference 📘

This document contains a complete technical breakdown of every class, method, property, and constant available in the `whatsapp-py` package.

---

## 📑 Table of Contents
- [Client](#client)
- [Structures](#structures)
  - [Message](#message)
  - [Chat & GroupChat](#chat--groupchat)
  - [Contact & BusinessContact](#contact--businesscontact)
  - [MessageMedia](#messagemedia)
  - [Location & Poll](#location--poll)
  - [ClientInfo](#clientinfo)
  - [Label](#label)
  - [Call](#call)
  - [Reaction](#reaction)
  - [PollVote](#pollvote)
  - [GroupNotification](#groupnotification)
- [Constants](#constants)
- [Authentication](#authentication)

---

## 🚀 Client
The main entry point for the library. Inherits from `EventEmitter`.

### Initialization
```python
from whatsapp import Client, LocalAuth

client = Client(auth_strategy=LocalAuth(), options={...})
```

#### `options` Configuration
| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `headless` | `bool` | `True` | Run browser in background. |
| `user_agent` | `str` | Default UA | Custom browser User Agent. |
| `auth_timeout_ms` | `int` | `30000` | Timeout for initial WA load. |
| `web_version` | `str` | Latest | Force specific WhatsApp Web version. |
| `web_version_cache` | `dict` | `{"type": "local"}` | How to cache WA scripts. |
| `qr_max_retries` | `int` | `0` | Times to retry QR generation. |

### Public Methods

#### Lifecycle
- **`await client.initialize()`**: Starts the browser, navigates to WA Web, and injects the JS bridge.
- **`await client.destroy()`**: Closes all browser instances and cleans up resources.
- **`await client.logout()`**: Logs out of the current session and destroys the browser.
- **`await client.get_state()`**: Returns the current connection state (`CONNECTED`, `PAIRING`, etc.).
- **`await client.reset_state()`**: Reconnects the internal WhatsApp socket.

#### Messaging
- **`await client.send_message(chat_id, content, options=None)`**: Sends a message.
  - `content`: `str`, `MessageMedia`, `Location`, or `Poll`.
  - `options`: `{"caption": str, "quoted_message_id": str, "mentions": [str], "linkPreview": bool}`.
- **`await client.send_reaction(message_id, emoji)`**: Sends an emoji reaction.
- **`await client.send_seen(chat_id)`**: Marks a chat as read.
- **`await client.search_messages(query, page=1, limit=20, chat_id=None)`**: Searches history.
- **`await client.get_message_by_id(message_id)`**: Retrieves a specific message.

#### Chats & History
- **`await client.get_chats()`**: Returns list of all `Chat` objects.
- **`await client.get_chat_by_id(chat_id)`**: Returns a single `Chat`.
- **`await client.get_channels()`**: Returns list of `Channel` objects.
- **`await client.archive_chat(chat_id)`**: Archives a chat.
- **`await client.unarchive_chat(chat_id)`**: Unarchives a chat.
- **`await client.pin_chat(chat_id)`**: Pins a chat.
- **`await client.unpin_chat(chat_id)`**: Unpins a chat.
- **`await client.mute_chat(chat_id, until=None)`**: Mutes a chat (pass `datetime` for `until`).
- **`await client.unmute_chat(chat_id)`**: Unmutes a chat.
- **`await client.sync_history(chat_id)`**: Requests a history sync for the chat.
- **`await client.get_pinned_messages(chat_id)`**: Returns list of pinned messages in a chat.

#### Contacts
- **`await client.get_contacts()`**: Returns list of all `Contact` objects.
- **`await client.get_contact_by_id(contact_id)`**: Returns a single `Contact`.
- **`await client.get_number_id(number)`**: Returns the internal ID for a phone number.
- **`await client.is_registered_user(number)`**: Check if a number is on WA.
- **`await client.get_profile_pic_url(contact_id)`**: Returns URL for profile picture.
- **`await client.get_common_groups(contact_id)`**: Returns IDs of groups shared with this contact.

#### Groups
- **`await client.create_group(title, participants)`**: Creates a group. Returns `{title, gid, participants}`.
- **`await client.accept_invite(invite_code)`**: Joins a group via code.
- **`await client.get_invite_info(invite_code)`**: Gets metadata for an invite code.
- **`await client.approve_group_membership_requests(group_id, options=None)`**: Approves pending join requests.
- **`await client.reject_group_membership_requests(group_id, options=None)`**: Rejects pending join requests.

#### Profile & Settings
- **`await client.get_wWeb_version()`**: Returns the current WhatsApp Web version string.
- **`await client.set_status(status_text)`**: Changes your "About" status.
- **`await client.set_display_name(name)`**: Changes your push name.
- **`await client.set_profile_picture(media)`**: Changes your profile picture.

#### Labels (Business)
- **`await client.get_labels()`**: Returns list of all `Label` objects.
- **`await client.get_label_by_id(label_id)`**: Returns a single `Label`.
- **`await client.get_chat_labels(chat_id)`**: Returns labels for a specific chat.

---

## 🏗 Structures

### `Message`
Represents a WhatsApp message.

#### Properties
- `id`: `dict` (internal ID structure)
- `body`: `str`
- `type`: `str` (chat, image, video, etc.)
- `from_`: `str` (sender ID)
- `to`: `str` (recipient ID)
- `author`: `str` (actual sender in groups)
- `from_me`: `bool`
- `has_media`: `bool`
- `has_quoted_msg`: `bool`
- `mentioned_ids`: `list[str]`
- `timestamp`: `int` (unix)

#### Methods
- **`await msg.reply(content, options=None)`**: Reply to this message.
- **`await msg.react(emoji)`**: React to this message.
- **`await msg.download_media()`**: Returns `MessageMedia`.
- **`await msg.get_quoted_message()`**: Returns the quoted `Message`.
- **`await msg.delete(everyone=False)`**: Deletes message.
- **`await msg.forward(chat_id)`**: Forwards message.
- **`await msg.pin(duration)`**: Pins message in the chat.
- **`await msg.unpin()`**: Unpins message.
- **`await msg.get_chat()`**: Returns the `Chat` object.

---

### `Chat` & `GroupChat`

#### `Chat` Methods
- **`await chat.send_message(content)`**
- **`await chat.send_seen()`**
- **`await chat.send_state_typing()`**
- **`await chat.send_state_recording()`**
- **`await chat.clear_state()`**
- **`await chat.fetch_messages(limit=50)`**
- **`await chat.clear_messages()`**
- **`await chat.delete()`**
- **`await chat.archive()` / `unarchive()`**
- **`await chat.pin()` / `unpin()`**
- **`await chat.mute(until)` / `unmute()`**
- **`await chat.sync_history()`**
- **`await chat.get_labels()`**

#### `GroupChat` (Extra)
- **`await group.add_participants([ids])`**
- **`await group.remove_participants([ids])`**
- **`await group.promote_participants([ids])`**
- **`await group.demote_participants([ids])`**
- **`await group.set_subject(title)`**
- **`await group.set_description(desc)`**
- **`await group.leave()`**
- **`await group.get_invite_code()`**
- **`await group.revoke_invite()`**
- **`await group.approve_membership_requests(options=None)`**
- **`await group.reject_membership_requests(options=None)`**

---

### `Contact` & `BusinessContact`

#### `Contact` Methods
- **`await contact.get_profile_pic_url()`**
- **`await contact.get_common_groups()`**
- **`await contact.block()` / `unblock()`**
- **`await contact.get_chat()`**

#### `BusinessContact` (Extra Properties)
- `description`, `email`, `website`, `address`, `categories`.

---

### `MessageMedia`
- **`mimetype`**: `str`
- **`data`**: `str` (Base64)
- **`filename`**: `str` (Optional)
- **`MessageMedia.from_file(path)`**: Helper.
- **`await MessageMedia.from_url(url)`**: Helper.

---

### `Call`
- `id`, `from_`, `is_video`, `is_group`, `from_me`, `timestamp`.
- **`await call.reject()`**: Rejects the incoming call.

---

### `GroupNotification`
- `id`, `body`, `type`, `timestamp`, `chat_id`, `author`, `recipient_ids`.
- **`await notification.get_chat()`**
- **`await notification.get_contact()`**
- **`await notification.reply(content)`**

---

## 🔢 Constants

### `Events`
List of all events emitted by `Client`.
- `AUTHENTICATED`, `AUTHENTICATION_FAILURE`, `READY`, `DISCONNECTED`.
- `MESSAGE_RECEIVED` (`'message'`), `MESSAGE_CREATE`, `MESSAGE_ACK`, `MESSAGE_EDIT`.
- `MESSAGE_REACTION`, `MEDIA_UPLOADED`, `CONTACT_CHANGED`.
- `GROUP_JOIN`, `GROUP_LEAVE`, `GROUP_ADMIN_CHANGED`, `GROUP_UPDATE`.
- `QR_RECEIVED` (`'qr'`), `LOADING_SCREEN`, `INCOMING_CALL`, `VOTE_UPDATE`.

### `MessageTypes`
- `TEXT`, `IMAGE`, `VIDEO`, `AUDIO`, `VOICE`, `DOCUMENT`, `STICKER`, `LOCATION`, `POLL_CREATION`, `REACTION`.

### `WAState`
- `CONNECTED`, `PAIRING`, `PROXYBLOCK`, `TIMEOUT`, `CONFLICT`, `UNLAUNCHED`, `UNPAIRED`.

### `MessageAck`
- `ACK_ERROR`: -1
- `ACK_PENDING`: 0
- `ACK_SERVER`: 1
- `ACK_DEVICE`: 2
- `ACK_READ`: 3
- `ACK_PLAYED`: 4

---

## 🔐 Authentication

### `LocalAuth`
Persists session data in a local folder.
```python
LocalAuth(client_id="bot-1", data_path="./.wwebjs_auth")
```

### `RemoteAuth`
Saves session data to a remote store (e.g. database/cloud) via custom handlers.
```python
RemoteAuth(store=my_store_instance, backup_sync_interval_ms=60000)
```

---
*End of Complete API Reference.*
