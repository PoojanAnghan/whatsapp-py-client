import asyncio
import sys
import argparse
from .client import Client
from .auth.local_auth import LocalAuth
from .auth.no_auth import NoAuth

async def start_client(client_id=None):
    """Run a basic ping-pong bot with optional client_id."""
    print(f"🚀 Starting WhatsApp-Py Bot (Client ID: {client_id or 'Temporary'})...")
    
    auth = LocalAuth(client_id=client_id) if client_id else NoAuth()
    client = Client(auth_strategy=auth)

    @client.on("qr")
    def on_qr(qr):
        print(f"\n📱 QR Code Received! Scan it in WhatsApp:\n{qr}\n")
        try:
            import qrcode
            qr_img = qrcode.make(qr)
            qr_img.save("qr.png")
            print("💡 QR saved to qr.png")
        except ImportError:
            print("⚠️ Install 'qrcode' to save as image: pip install qrcode")

    @client.on("ready")
    async def on_ready():
        print("✅ Bot is ready and online!")
        print("💡 Send '!ping' to this number to test.")

    @client.on("message")
    async def on_message(msg):
        if msg.body == "!ping":
            await msg.reply("pong 🏓")
            print(f"💬 Replied to ping from {msg.from_}")

    try:
        await client.initialize()
        # Keep running
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\n👋 Stopping bot...")
        await client.destroy()

def main():
    parser = argparse.ArgumentParser(description="WhatsApp-Py CLI Tool")
    parser.add_argument("--client-id", type=str, help="Persistent session ID")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Show browser window")

    args = parser.parse_args()

    try:
        asyncio.run(start_client(client_id=args.client_id))
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
