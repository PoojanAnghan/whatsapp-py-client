# 🚀 whatsapp-py (wwebjs-python-client)

`whatsapp-py` is a production-grade, high-performance WhatsApp Web automation library for Python. Built on top of **Playwright**, it provides a stable and feature-rich API that mirrors the popular `whatsapp-web.js` Node.js library.

> [!IMPORTANT]
> **Production Stable:** This version includes the "Unbreakable" bridge system, which prevents crashes during WhatsApp Web updates by dynamically mapping internal JS modules.

---

## 📦 Installation

### 1. For Developers (Local Setup)
If you are working on a project and want to use the library from source:
```bash
# Clone the repository
git clone https://github.com/PoojanAnghan/whatsapp-py-client
cd whatsapp-py

# Install in editable mode
pip install -e .

# Install browser dependencies
python -m playwright install chromium
```

### 2. For Production
```bash
pip install whatsapp-py
python -m playwright install chromium
```

---

## 📖 Basic Usage Pattern

Every `whatsapp-py` project follows this simple 3-step lifecycle:

1. **The Setup**: Import the core classes and choose an authentication strategy.
2. **The Logic (Events)**: Define what happens when messages arrive or status changes.
3. **The Launch**: Initialize the engine to start the browser.

```python
from whatsapp import Client, LocalAuth
import asyncio

# 1. Setup
client = Client(auth_strategy=LocalAuth())

# 2. Logic
@client.on('message')
async def handle_message(msg):
    if msg.body == 'Hi':
        await msg.reply('Hello!')

# 3. Launch
asyncio.run(client.initialize())
```

---

## 🚀 Quick Start

Build a bot that responds and then **edits** its own message:

```python
import asyncio
from whatsapp import Client, LocalAuth

async def main():
    # Use LocalAuth to stay logged in after scanning once
    client = Client(auth_strategy=LocalAuth(client_id="my-bot"))

    @client.on('qr')
    async def on_qr(qr):
        # This saves the QR to a file you can open
        import qrcode
        img = qrcode.make(qr)
        img.save("qr.png")
        print("📥 QR Code saved to qr.png. Scan it now!")

    @client.on('ready')
    async def on_ready():
        print(f"✅ Bot is Online! Logged in as: {client.info.pushname}")

    @client.on('message')
    async def on_message(msg):
        if msg.body == "!ping":
            # 1. Reply to the user
            reply = await msg.reply("Ping...")
            
            # 2. Wait and then EDIT the message!
            await asyncio.sleep(2)
            await reply.edit("Pong! 🏓")

    await client.initialize()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔑 How to Login

1. **Start your script:** Run your Python file (e.g., `python bot.py`).
2. **Find the QR:** A file named `qr.png` will appear in your project directory.
3. **Scan it:** Open WhatsApp on your phone -> **Settings** -> **Linked Devices** -> **Link a Device** and scan the code on your screen.
4. **Done:** Once scanned, the `ready` event will fire and your bot is online!

> [!TIP]
> Since we use `LocalAuth`, you only need to do this **once**. The next time you start the bot, it will log in automatically using your saved session.

---

## 🛠 Features & Capabilities

### ✨ Message Editing
The most requested feature. You can edit any message sent by the bot.
```python
msg = await client.send_message(chat_id, "Old Text")
await msg.edit("New Text ✨")
```

### 📡 Advanced Event Tracking
Monitor exactly when your messages are delivered or read.
```python
@client.on('message_ack')
async def on_ack(msg, ack):
    # ack: 1 (Sent), 2 (Delivered), 3 (Read)
    status = {1: "Sent", 2: "Delivered", 3: "Read"}.get(ack, "Unknown")
    print(f"Message {msg.id.id} is now {status}")
```

### 📁 Media Support
Send images, documents, and videos with ease.
```python
from whatsapp import MessageMedia

media = MessageMedia.from_file("report.pdf")
await client.send_message(chat_id, media, options={"caption": "Monthly Report"})
```

---

## 🔑 Authentication Strategies

| Strategy | Description | Best For |
| :--- | :--- | :--- |
| `LocalAuth` | Saves session to `.wwebjs_auth/` folder. | Production bots, local services. |
| `NoAuth` | Temporary session, scan QR every time. | Testing, one-off scripts. |

## 📡 Full Event Reference

The `Client` emits these events. Use `@client.on('event_name')` to listen.

| Event | Payload | Description |
| :--- | :--- | :--- |
| `qr` | `str` | New QR code string generated. |
| `ready` | `None` | Client is fully logged in and synced. |
| `authenticated` | `None` | Session is valid (emitted before `ready`). |
| `auth_failure` | `str` | Authentication failed (e.g., session expired). |
| `message` | `Message` | New message received. |
| `message_create` | `Message` | Any message created (even by the bot). |
| `message_ack` | `Message, ack` | Status update (Sent/Delivered/Read). |
| `message_edit` | `Message, new, old`| A message was edited. |
| `message_revoked_everyone` | `Message` | Message was deleted for everyone. |
| `group_join` | `Notification` | A user joined a group. |
| `group_leave` | `Notification` | A user left/was removed. |
| `group_update` | `Notification` | Group settings changed. |
| `disconnected` | `str` | Client was logged out. |

---

## 🏗 API Reference

### The `Message` Class
| Property/Method | Type | Description |
| :--- | :--- | :--- |
| `body` | `str` | Text content of the message. |
| `from_` | `str` | ID of the sender (e.g. `9199... @c.us`). |
| `to` | `str` | ID of the recipient. |
| `timestamp` | `int` | Unix timestamp. |
| `from_me` | `bool` | `True` if sent by the bot. |
| `has_media` | `bool` | `True` if message has an attachment. |
| `reply(text)` | `Method` | Reply to this message (quotes it). |
| `edit(text)` | `Method` | Edit this message (if sent by bot). |
| `react(emoji)` | `Method` | Add a reaction. |
| `get_chat()` | `Method` | Returns the `Chat` object for this message. |

### The `Chat` Class
| Property/Method | Type | Description |
| :--- | :--- | :--- |
| `id` | `str` | Serialized ID of the chat. |
| `name` | `str` | Display name of the chat/group. |
| `is_group` | `bool` | `True` if it's a group chat. |
| `send_message(text)` | `Method` | Send a message to this chat. |
| `send_state_typing()` | `Method` | Show "typing..." indicator. |
| `clear_state()` | `Method` | Stop showing "typing/recording". |

---

## 🛠 Advanced Configuration

You can customize the `Client` behavior:

```python
client = Client(
    auth_strategy=LocalAuth(),
    playwright_options={
        "headless": True,        # Set to False to see the browser window
        "proxy": {"server": "http://..."},
    }
)
```

---

## ❓ FAQ & Troubleshooting

#### 1. Why is the QR code not appearing in my terminal?
Ensure you have `qrcode` installed (`pip install qrcode`). If you are on a server, use the `qr` event to save it to a file.

#### 2. Can I run multiple bots?
Yes! Just give each one a unique `client_id` in `LocalAuth(client_id="bot-1")`.

#### 3. How do I send a message to a new number?
Use the full ID format: `[phone_number]@c.us` (e.g., `919876543210@c.us`).

---

## 🛡 "Unbreakable" Bridge System
Unlike other libraries that hardcode WhatsApp's internal JavaScript names (which change weekly), `whatsapp-py` uses a **Dynamic Module Resolver**. 

- **How it works:** On startup, the library scans the WhatsApp memory to find the current names of modules like `Msg`, `Chat`, and `Cmd`.
- **The Result:** Your bot keeps working even after WhatsApp updates their website.

---

## 💻 CLI Tools
You can launch the client directly from your terminal for testing:
```bash
# Start a basic instance
whatsapp-py --client-id "test-session"
```

---

---

## 🏛 Architectural Guidance: Building a Robust Orchestrator

When moving from a simple script to a production service (like a backend for an app), you should follow an **Orchestrator Pattern**. 

### 1. Separate the "Engine" from "Logic"
Don't put your business logic (like database calls or complex API math) inside the `@client.on` listeners. Instead, use the listeners to trigger **Service Tasks**.
*   **Why?** If your business logic crashes, you don't want it to kill the entire WhatsApp browser process.

### 2. Handle Graceful Shutdowns
Always catch system signals (`SIGINT`, `SIGTERM`) to call `await client.destroy()`. 
*   **Why?** If you don't close the browser properly, you might leave "ghost" processes running on your server, which will eventually eat up all your RAM.

### 3. The "State" Monitor
In production, create a "Health Check" that monitors the `client.info` and `socket state`. 
*   **Guidance:** If the bot enters a `DISCONNECTED` state for more than 5 minutes, your orchestrator should automatically trigger a `client.initialize()` to attempt a reconnection.

### 4. Headless Management
For servers, always run with `headless: True`. However, during your **first deployment**, you should temporarily set it to `False` (or use a VNC/Remote Desktop) to ensure the QR code is scanned correctly if you aren't using the `qr.png` method.

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

*Built with ❤️ by Poojan Anghan.*
