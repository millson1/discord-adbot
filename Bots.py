import os
import asyncio
import sys
import subprocess
import shutil

tokens = ["token3", "token2", "token1"]
launch_delay = 40 * 60
replied_users = set()

async def launch_scripts():
    for i, token in enumerate(tokens, start=1):
        # Check the operating system and use appropriate command
        if sys.platform == "win32":
            command = f"start python discord_selfbot_script.py {token}"
            os.system(command)
        else:  # Linux or macOS
            # Check if screen is installed
            screen_path = shutil.which("screen")
            if not screen_path:
                print("Warning: 'screen' is not installed. Using subprocess instead.")
                subprocess.Popen(["python3", "discord_selfbot_script.py", token], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
            else:
                # Create a unique screen session name
                session_name = f"discord-bot-{i}"
                # Launch the script in a screen session
                screen_cmd = ["screen", "-dmS", session_name, "python3", "discord_selfbot_script.py", token]
                subprocess.run(screen_cmd)
                print(f"Started bot in screen session: {session_name}")
                print(f"You can attach to this session with: screen -r {session_name}")
        
        print(f"Script {i} launched with token: {token}")
        if i < len(tokens):
            print(f"Waiting {launch_delay // 60} minutes before launching the next script...")
            await asyncio.sleep(launch_delay)

async def main():
    await launch_scripts()
    await asyncio.sleep(launch_delay * len(tokens))

if __name__ == "__main__":
    asyncio.run(main())
