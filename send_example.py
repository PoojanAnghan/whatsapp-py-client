import asyncio
from whatsapp import Client, LocalAuth

async def main():
    # 1. Initialize the client with LocalAuth (persists session)
    client = Client(auth_strategy=LocalAuth(client_id="my-session"))

    @client.on('qr')
    async def on_qr(qr):
        print("Scan this QR code in WhatsApp!")

    @client.on('ready')
    async def on_ready():
        print("Bot is ready!")
        
        # 2. Define the recipient (Phone number + @c.us)
        # Change this to a real number you want to message
        recipient_id = "910000000000@c.us" 
        
        # 3. Send the message
        print(f"Sending message to {recipient_id}...")
        try:
            await client.send_message(recipient_id, "Hello from wwebjs-python-client! 🚀")
            print("✅ Message sent successfully!")
        except Exception as e:
            print(f"❌ Failed to send message: {e}")

    await client.initialize()

if __name__ == "__main__":
    asyncio.run(main())
