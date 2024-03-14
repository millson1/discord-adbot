import os
import asyncio

tokens = ["token3", "token2", "token1"]
launch_delay = 40 * 60
replied_users = set()

async def launch_scripts():
    for i, token in enumerate(tokens, start=1):
        command = f"start python discord_selfbot_script.py {token}"
        os.system(command)
        print(f"Script {i} launched with token: {token}")
        if i < len(tokens):
            print(f"Waiting {launch_delay // 60} minutes before launching the next script...")
            await asyncio.sleep(launch_delay)

async def main():
    await launch_scripts()
    await asyncio.sleep(launch_delay * len(tokens))

if __name__ == "__main__":
    asyncio.run(main())
