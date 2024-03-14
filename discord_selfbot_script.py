import discord
import sys
import random
import time
import asyncio

if len(sys.argv) != 2:
    print("Usage: python discord_selfbot_script.py <token>")
    sys.exit(1)

TOKEN = sys.argv[1]
CHANNEL_ID = 910667265760956478 # Set your channel ID

messages = [
    "Hello World",
    """test
       test
       test""" # Use """ for messages with newlines
]

client = discord.Client()
replied_users = set()

@client.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel) and message.author != client.user:
        await handle_dm(message)
    else:
        pass


async def handle_dm(message):
    if message.author.id not in replied_users:
        replied_users.add(message.author.id)
        sleep_time = random.randint(50, 80)
        print(f"Sleeping for {sleep_time} seconds...")
        await asyncio.sleep(sleep_time)
        await message.channel.send(
            "Specify your DM message here") #Edit this


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
            await asyncio.sleep(7200)  # 2 hours
            await send_message()
    except Exception as e:
        print("An error occurred:", e)

client.run(TOKEN)
