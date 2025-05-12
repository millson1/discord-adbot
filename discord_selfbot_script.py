import os
import discord
import sys
import random
import asyncio
import json
from datetime import datetime

if len(sys.argv) != 2:
    print("Usage: python discord_selfbot_script.py <token>")
    sys.exit(1)

TOKEN = sys.argv[1]
CHANNEL_ID = 123456789012345678  # Replace with your channel ID
REPLIED_USERS_FILE = "replied_users.json"
MESSAGE_DELAY = (50, 200)  # Min, max seconds before replying to DMs
DM_CHECK_INTERVAL = 60  # Check for new DMs every 60 seconds

# Placeholder messages
messages = [
    "Placeholder message 1",
    "Placeholder message 2",
    "Placeholder message 3"
]

class SelfBot(discord.Client):
    def __init__(self):
        super().__init__()
        self.replied_users = self.load_replied_users()
        self.post_task = None
        self.dm_check_task = None
        self.lock = asyncio.Lock()
        self.last_dm_check = datetime.now()

    def load_replied_users(self):
        try:
            if os.path.exists(REPLIED_USERS_FILE):
                with open(REPLIED_USERS_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
                    return set()
            return set()
        except Exception as e:
            print(f"Error loading replied users: {e}")
            return set()

    async def save_replied_users(self):
        try:
            async with self.lock:
                with open(REPLIED_USERS_FILE, 'w') as f:
                    json.dump(list(self.replied_users), f)
        except Exception as e:
            print(f"Error saving replied users: {e}")

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.post_task = self.loop.create_task(self.post_periodically())
        self.dm_check_task = self.loop.create_task(self.check_dms_periodically())

    async def post_periodically(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                channel = self.get_channel(CHANNEL_ID)
                if channel:
                    await channel.send(random.choice(messages))
                    print(f"Posted message in {channel.name}")
            except Exception as e:
                print(f"Error posting message: {e}")
            
            await asyncio.sleep(random.randint(7200, 7400))  # 2 hours-ish

    async def check_dms_periodically(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                print("Checking DMs...")
                for channel in self.private_channels:
                    if isinstance(channel, discord.DMChannel):
                        async for message in channel.history(limit=20, after=self.last_dm_check):
                            if message.author != self.user:
                                await self.handle_dm(message)
                self.last_dm_check = datetime.now()
            except Exception as e:
                print(f"Error checking DMs: {e}")
            await asyncio.sleep(DM_CHECK_INTERVAL)

    async def on_message(self, message):
        if message.author == self.user:
            return
        
        if isinstance(message.channel, discord.DMChannel):
            await self.handle_dm(message)

    async def handle_dm(self, message):
        user_id = message.author.id
        async with self.lock:
            if user_id not in self.replied_users:
                print(f"New DM from {message.author}")
                
                delay = random.randint(*MESSAGE_DELAY)
                await asyncio.sleep(delay)
                
                try:
                    await message.channel.send("Placeholder reply message")
                    self.replied_users.add(user_id)
                    await self.save_replied_users()
                    print(f"Replied to {message.author}")
                except Exception as e:
                    print(f"Failed to reply to {message.author}: {e}")
            else:
                print(f"Already replied to {message.author}")

if __name__ == "__main__":
    bot = SelfBot()
    
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\nBot shutting down...")
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        if bot.loop.is_running():
            bot.loop.run_until_complete(bot.save_replied_users())
        input("Press Enter to exit...")
