import discord
import sys
import random
import time
import asyncio
import os
import json

if len(sys.argv) != 2:
    print("Usage: python discord_selfbot_script.py <token>")
    sys.exit(1)

TOKEN = sys.argv[1]
CHANNEL_ID = 910667265760956478  # Set your channel ID
REPLIED_USERS_FILE = "replied_users.json"

def load_replied_users():
    if os.path.exists(REPLIED_USERS_FILE):
        try:
            with open(REPLIED_USERS_FILE, 'r') as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Error loading replied users: {e}")
            return set()
    else:
        return set()

def save_replied_users(users):
    try:
        with open(REPLIED_USERS_FILE, 'w') as f:
            json.dump(list(users), f)
    except Exception as e:
        print(f"Error saving replied users: {e}")

# Just one example message
messages = [
    """
    Java or Bedrock (include version): **Java 1.21**
    Realm/Server/World (specify which, not a name): **Server**
    Number of players: **15 currently, room for 5 more**
    Length of Play Session: **3+ hours**
    Gametype: **Survival with economy**
    Language: **English**
    """
]

client = discord.Client()
replied_users = load_replied_users()

@client.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel) and message.author != client.user:
        await handle_dm(message)

async def handle_dm(message):
    global replied_users
    if message.author.id not in replied_users:
        replied_users.add(message.author.id)
        save_replied_users(replied_users)
        sleep_time = random.randint(50, 80)
        print(f"Sleeping for {sleep_time} seconds...")
        await asyncio.sleep(sleep_time)
        await message.channel.send("Hey! Thanks for the message 🙂")  # Clean reply

async def send_message():
    try:
        print("Bot is ready.")
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            print("Channel found.")
            message = random.choice(messages)
            print("Sending message:", message)
            await channel.send(message)
            print("Message sent.")
        else:
            print("Channel not found.")
    except Exception as e:
        print("An error occurred:", e)

@client.event
async def on_ready():
    try:
        await send_message()
        while True:
            await asyncio.sleep(random.randint(7200, 7400))  # Wait ~2 hours
            await send_message()
            print(f"Current Username: {client.user.name}")
    except Exception as e:
        print("An error occurred:", e)

client.run(TOKEN)
