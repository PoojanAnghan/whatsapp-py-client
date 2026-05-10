"""
example.py — mirrors example.js from whatsapp-web.js
Run: python example.py
"""
import asyncio
import sys
from whatsapp import Client, LocalAuth, MessageMedia, Location, Poll

# Increase recursion limit for deep JSON objects from WA
sys.setrecursionlimit(5000)

client = Client(auth_strategy=LocalAuth(), options={"headless": True})


@client.on("qr")
async def on_qr(qr: str):
    print(f"\n📱 Scan QR Code:\n{qr}\n")
    try:
        import qrcode
        qr_img = qrcode.make(qr)
        qr_img.save("qr.png")
        print("QR saved to qr.png")
    except ImportError:
        pass


@client.on("authenticated")
async def on_authenticated(_):
    print("✅ Authenticated!")


@client.on("auth_failure")
async def on_auth_failure(msg):
    print(f"❌ Auth failure: {msg}")


@client.on("ready")
async def on_ready():
    # Wait for the page to settle after sync
    await asyncio.sleep(10)
    version = await client.get_wWeb_version()
    print(f"🚀 Client ready! WA Web version: {version}")
    
    # Example: Send a message to a specific number on startup
    target_number = "1234567890@c.us" # Replace with your target ID
    await client.send_message(target_number, "Hello! I am now online and ready.")


@client.on("message")
async def on_message(msg):
    # Guard for non-text messages (e.g. system msgs, stickers without text)
    if not msg.body:
        return

    print(f"💬 [{msg.from_}]: {msg.body}")

    if msg.body == "!ping":
        await client.send_message(msg.from_, "pong 🏓")

    elif msg.body == "!ping reply":
        await msg.reply("pong 🏓")

    elif msg.body == "!info":
        info = client.info
        await client.send_message(
            msg.from_,
            f"*Bot Info*\nName: {info.pushname}\nNumber: {info.wid.get('user')}\nPlatform: {info.platform}",
        )

    elif msg.body == "!chats":
        chats = await client.get_chats()
        await client.send_message(msg.from_, f"You have {len(chats)} chats.")

    elif msg.body == "!mediainfo" and msg.has_media:
        media = await msg.download_media()
        if media:
            await msg.reply(
                f"*Media Info*\nMIME: {media.mimetype}\nFile: {media.filename}\nSize: {media.filesize} bytes"
            )

    elif msg.body == "!location":
        await msg.reply(Location(37.422, -122.084, name="Googleplex", address="Mountain View, CA"))

    elif msg.body == "!poll":
        await msg.reply(Poll("Cats or Dogs?", ["Cats 🐱", "Dogs 🐶"], allow_multiple_answers=False))

    elif msg.body == "!reaction":
        await msg.react("👍")

    elif msg.body == "!delete" and msg.has_quoted_msg:
        quoted = await msg.get_quoted_message()
        if quoted and quoted.from_me:
            await quoted.delete(everyone=True)

    elif msg.body == "!typing":
        chat = await msg.get_chat()
        await chat.send_state_typing()

    elif msg.body.startswith("!status "):
        new_status = msg.body[8:]
        await client.set_status(new_status)
        await msg.reply(f"Status updated to: {new_status}")


@client.on("message_ack")
async def on_ack(msg, ack):
    ack_names = {-1: "ERROR", 0: "PENDING", 1: "SERVER", 2: "DEVICE", 3: "READ", 4: "PLAYED"}
    print(f"📬 ACK [{ack_names.get(ack, ack)}]: {msg.id.get('_serialized')}")


@client.on("call")
async def on_call(call):
    print(f"📞 Incoming call from {call.from_} (video={call.is_video})")
    await call.reject()
    await client.send_message(call.from_, "Sorry, I don't accept calls.")


@client.on("disconnected")
async def on_disconnected(reason):
    print(f"🔌 Disconnected: {reason}")


async def main():
    await client.initialize()
    print("🚀 Bot is live! Press Ctrl+C to stop.")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")
