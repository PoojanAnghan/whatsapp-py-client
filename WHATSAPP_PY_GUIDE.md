# WhatsApp-Py: The Complete User Guide 🚀

`whatsapp-py` is a powerful, high-performance Python automation library for WhatsApp Web. Built on **Playwright**, it provides a stable and feature-rich API for building bots, notifications, and multi-tenant messaging systems.

---

## 🏗 Getting Started

### 1. Installation
Install the package and the required browser engine:

```bash
pip install playwright pyee httpx Pillow aiofiles qrcode
python -m playwright install chromium
```

### 2. Your First Bot
A simple "Ping-Pong" bot to get you started:

```python
import asyncio
from whatsapp import Client, LocalAuth

async def main():
    # Use LocalAuth to stay logged in after scanning once
    client = Client(auth_strategy=LocalAuth(client_id="main-bot"))

    @client.on('qr')
    async def on_qr(qr):
        print("Scan this QR code in WhatsApp!")

    @client.on('ready')
    async def on_ready():
        print(f"Logged in as {client.info.pushname}!")

    @client.on('message')
    async def on_message(msg):
        if msg.body.lower() == "!ping":
            await msg.reply("pong 🏓")

    await client.initialize()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔑 Authentication Strategies

### LocalAuth (Recommended)
Stores session data (cookies, storage) in a local directory. This ensures you don't have to scan the QR code every time you restart the script.

```python
from whatsapp import LocalAuth
client = Client(auth_strategy=LocalAuth(client_id="unique-session-id"))
```
*   **Data Location**: Sessions are stored in `.wwebjs_auth/session-<client_id>`.
*   **Multi-tenant**: You can run multiple instances by giving each a unique `client_id`.

### NoAuth
Default strategy. It does not save any session data. Useful for testing or one-time runs.

---

## 📩 Advanced Messaging

### 1. Replying and Reacting
```python
@client.on('message')
async def handle_message(msg):
    # Reply to the message
    await msg.reply("This is a reply!")

    # React with an emoji
    await msg.react("🔥")
```

### 2. Sending Media
You can send images, videos, audio, and documents using `MessageMedia`.

```python
from whatsapp import MessageMedia

# Send an image from a file
media = MessageMedia.from_file("./docs/image.png")
await client.send_message("1234567890@c.us", media, options={"caption": "Check this out!"})

# Send a PDF from a URL
pdf_media = await MessageMedia.from_url("https://your-domain.com/report.pdf")
await client.send_message(chat_id, pdf_media)
```

### 3. Interactive Polls
Polls are a great way to engage users.

```python
from whatsapp import Poll

@client.on('message')
async def on_message(msg):
    if msg.body == "!vote":
        poll = Poll("Select an option:", ["Option A", "Option B", "Option C"])
        await msg.reply(poll)

@client.on('vote_update')
async def on_vote(vote):
    print(f"User {vote.voter} voted for {vote.selected_options}")
```

---

## 👥 Group Management

Manage groups programmatically with ease.

```python
# Create a new group
res = await client.create_group("Dev Team", ["1234567890@c.us", "0987654321@c.us"])
group_id = res['gid']['_serialized']

# Get a GroupChat object
group = await client.get_chat_by_id(group_id)

# Perform actions
await group.set_description("Official developers group.")
await group.add_participants(["1234567890@c.us"])
await group.promote_participants(["1234567890@c.us"]) # Make admin
```

---

## 🛡 Best Practices & Bot Detection

WhatsApp has strict anti-spam measures. Follow these tips to keep your account safe:

1.  **Human-like Delays**: Never respond instantly. Use `asyncio.sleep()` to add a random delay.
    ```python
    import random
    await asyncio.sleep(random.uniform(1.5, 4.0))
    await msg.reply("Hello!")
    ```
2.  **Avoid Cold Messaging**: Don't send messages to hundreds of numbers who haven't saved your contact. This is the fastest way to get banned.
3.  **Typing Indicator**: Use `await chat.send_state_typing()` before sending a message to simulate a human user.
4.  **Graceful Shutdown**: Always call `await client.destroy()` when closing your app to ensure the browser processes are cleaned up.

---

## ⚙ Advanced Configuration

### High Performance Mode
If you have a large account with thousands of messages, increase the recursion limit to prevent crashes during JSON serialization:

```python
import sys
sys.setrecursionlimit(5000)
```

### Visual Debugging
To see what the browser is doing, turn off headless mode:

```python
client = Client(options={"headless": False})
```

---

## ❓ Troubleshooting

*   **"WWebJS never became available"**: Usually caused by slow internet or a very old WhatsApp Web version. The library retries automatically, but ensure your connection is stable.
*   **QR Code not appearing**: Check if `qrcode` is installed (`pip install qrcode`). If not, the library will only print the QR string to the console.
*   **Memory Usage**: Each client instance takes ~200MB of RAM. If running on a low-spec VPS, limit the number of simultaneous clients.

---

*Need more details? Check the [API Reference](./WHATSAPP_PY_API_REFERENCE.md).*
