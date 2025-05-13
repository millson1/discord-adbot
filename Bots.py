import os
import asyncio
import sys
import subprocess
import shutil
import argparse

# Define your token list
tokens = ["TOKEN1", "TOKEN2"]

DEFAULT_LAUNCH_DELAY = 24 * 60 #Enter staggered launch delay. This for example will launch a bot every 24 minutes until all are launched.


##### DO NOT TOUCH BELOW. NO CONFIGS HERE


async def launch_scripts(simultaneous=False, delay=DEFAULT_LAUNCH_DELAY):
    print(f"Launching {len(tokens)} bot(s) with {'simultaneous' if simultaneous else 'sequential'} mode")
    
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
        
        print(f"Script {i} launched with token: {token[:15]}...{token[-5:]}")  # Only show part of token for security
        
        # If not simultaneous and there are more tokens to process, wait
        if not simultaneous and i < len(tokens):
            print(f"Waiting {delay // 60} minutes before launching the next script...")
            await asyncio.sleep(delay)

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Launch Discord selfbots")
    parser.add_argument("-s", "--simultaneous", action="store_true", 
                       help="Launch all bots simultaneously without delay")
    parser.add_argument("-d", "--delay", type=int, default=DEFAULT_LAUNCH_DELAY // 60,
                       help="Delay in minutes between launching bots (default: 30)")
    
    # Handle the case when the script is run directly from command line
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', '-s', '--simultaneous', '-d', '--delay']:
        args = parser.parse_args()
        delay_seconds = args.delay * 60
    else:
        # If no relevant args, check for a simple -s flag for backward compatibility
        args = parser.parse_args([])
        args.simultaneous = "-s" in sys.argv
        delay_seconds = DEFAULT_LAUNCH_DELAY
    
    # Launch the scripts with appropriate settings
    await launch_scripts(simultaneous=args.simultaneous, delay=delay_seconds)
    
    # If we're waiting between launches, wait one more delay period at the end
    if not args.simultaneous:
        total_wait = delay_seconds * (len(tokens) - 1)
        print(f"All scripts launched. Total wait time was {total_wait // 60} minutes.")
    else:
        print("All scripts launched simultaneously.")

if __name__ == "__main__":
    asyncio.run(main())
