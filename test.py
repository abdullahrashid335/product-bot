import os
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1362488967227768916  # Replace with the exact channel ID (no quotes)

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    try:
        channel = await client.fetch_channel(CHANNEL_ID)
        await channel.send("✅ This is a test message from the bot.")
        print("✅ Message sent successfully.")
    except discord.Forbidden:
        print("❌ Forbidden: Bot does not have permission to access the channel.")
    except discord.HTTPException as e:
        print(f"❌ HTTP error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

client.run(TOKEN)
