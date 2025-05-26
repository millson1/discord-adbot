import os
import asyncio
import sys
import subprocess
import shutil
import argparse

# --- USER CONFIGURATION: TOKENS ---
# Replace the example tokens below with your actual Discord user tokens.
# WARNING: Using user tokens for automation violates Discord ToS and can lead to account suspension.
tokens = [
    "YOUR_FIRST_DISCORD_USER_TOKEN_HERE",
    "YOUR_SECOND_DISCORD_USER_TOKEN_HERE",
    # "YOUR_THIRD_DISCORD_USER_TOKEN_HERE", # Add more tokens as needed, one per line
]
# --- END OF USER CONFIGURATION ---

# Default delay between launching script *processes* (if not simultaneous)
DEFAULT_PROCESS_LAUNCH_DELAY = 5 # seconds, to be gentle on the system
SCRIPT_NAME = "discord_selfbot_script.py" # Ensure this matches your selfbot script's filename

async def stop_all_bots():
    print("Attempting to stop all existing bot instances...")
    stopped_count = 0

    # Check if SCRIPT_NAME is a placeholder; if so, can't effectively stop.
    if SCRIPT_NAME == "discord_selfbot_script.py" and not os.path.exists(SCRIPT_NAME):
        print(f"Warning: Main script '{SCRIPT_NAME}' not found. Stop command might be ineffective if script name was changed but not updated here.")

    script_name_for_ps = SCRIPT_NAME.replace("_", "[_\\- ]?") # More flexible matching for process names

    if sys.platform == "win32":
        # Try to kill python.exe and pythonw.exe processes running the script
        # This is a bit broad, be cautious if you run other unrelated python scripts with similar names.
        # Using taskkill with a filter based on window title if `start` command was used with a title.
        # However, /B flag for start means no new window.
        # WMIC is more reliable for command line.
        cmd_python = [
            "wmic", "process", "where",
            f"(name='python.exe' or name='pythonw.exe') and commandline like '%{script_name_for_ps}%'",
            "delete"
        ]
        try:
            result = subprocess.run(cmd_python, capture_output=True, text=True, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
            if "No instance(s) available." not in result.stdout and "No instance(s) available." not in result.stderr :
                print(f"WMIC attempt to terminate processes matching '{script_name_for_ps}' sent.")
                # WMIC delete doesn't give a clear count easily.
            else:
                print(f"WMIC: No Python processes found running a script like '{script_name_for_ps}'.")
        except FileNotFoundError:
            print("WMIC command not found. Cannot stop processes on Windows automatically using WMIC.")
        except subprocess.CalledProcessError as e:
            print(f"Error stopping processes on Windows with WMIC: {e}")
    else:  # Linux or macOS
        screen_path = shutil.which("screen")
        if screen_path:
            print("Attempting to stop screen sessions...")
            # Assuming screen sessions are named discord-bot-0, discord-bot-1, etc.
            for i in range(len(tokens) + 5): # Check a few more than current tokens just in case
                session_name = f"discord-bot-{i}"
                screen_quit_cmd = [screen_path, "-S", session_name, "-X", "quit"]
                result = subprocess.run(screen_quit_cmd, capture_output=True, text=True)
                if "No screen session found" not in result.stderr and result.returncode == 0:
                    print(f"Successfully sent quit command to screen session: {session_name}")
                    stopped_count +=1
                elif "No screen session found" not in result.stderr and result.stderr and "screen is terminating" not in result.stderr.lower():
                     print(f"Screen quit command for {session_name} had stderr: {result.stderr.strip()}")
        else:
            print("'screen' command not found. Cannot stop screen sessions by name.")

        print(f"Attempting to pkill processes matching 'python.*{script_name_for_ps}'.")
        pkill_cmd = ["pkill", "-f", f"python.*{script_name_for_ps}"]
        try:
            result = subprocess.run(pkill_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"pkill command '{' '.join(pkill_cmd)}' likely successful (signal sent).")
                # pkill doesn't easily give a count of killed processes, just success/failure of sending signal
            elif "no process found" not in result.stderr.lower() and result.stderr: # pkill often returns 1 if no process found
                 print(f"pkill command '{' '.join(pkill_cmd)}' stderr: {result.stderr.strip()}")
            else:
                 print(f"pkill: No processes found matching 'python.*{script_name_for_ps}'.")

        except FileNotFoundError:
            print(f"Command 'pkill' not found. Cannot pkill processes.")
        
    if stopped_count > 0 : # Only relevant for screen
        print(f"Stopped {stopped_count} screen session(s). Other processes were signaled via WMIC/pkill.")
    print("Finished attempt to stop existing bots. Please verify manually if needed.")


async def launch_scripts(simultaneous_processes=False, process_launch_delay_s=DEFAULT_PROCESS_LAUNCH_DELAY, disable_stagger_flag=False):
    num_bots = len(tokens)
    if num_bots == 0 or (num_bots == 1 and tokens[0].startswith("YOUR_")) :
        print("Error: No valid tokens found in the 'tokens' list or only placeholders are present.")
        print("Please add your Discord user tokens to the 'tokens' list in bots.py.")
        return

    launch_mode = "simultaneously (process-wise)" if simultaneous_processes else f"sequentially with a {process_launch_delay_s}s delay between processes"
    print(f"Launching {num_bots} bot script process(es) {launch_mode}")
    print("NOTE: Actual Discord post staggering is handled *within* each selfbot script, unless disabled by the '-r' internal flag.")
    if disable_stagger_flag:
        print("The '-r' flag WILL be passed to each selfbot instance, disabling their internal initial post staggering.")


    for i, token in enumerate(tokens): # i will be 0-indexed
        if token.startswith("YOUR_") or len(token) < 50: # Basic check for placeholder or invalid token
            print(f"Warning: Token at index {i} looks like a placeholder or is too short. Skipping.")
            print(f"Token: '{token[:20]}...'")
            continue

        instance_index = i # Use 0-based index for the script
        
        base_command_args = ["python3" if sys.platform != "win32" else "python", SCRIPT_NAME, token, str(instance_index)]
        if disable_stagger_flag:
            base_command_args.append("-r") # Add the -r flag for the selfbot script

        if sys.platform == "win32":
            # Use start /B to run in background without new window.
            # Title helps identify process, but /B might make title less visible in task manager.
            win_command = ["start", f"DiscordBotInst{instance_index}", "/B"] + base_command_args
            # os.system needs a string
            os.system(" ".join(win_command))
        else:  # Linux or macOS
            screen_path = shutil.which("screen")
            if not screen_path:
                print(f"Warning: 'screen' not installed for bot {instance_index}. Using detached subprocess.")
                subprocess.Popen(base_command_args,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
            else:
                session_name = f"discord-bot-{instance_index}" # 0-indexed session name
                screen_cmd = [screen_path, "-dmS", session_name] + base_command_args
                subprocess.run(screen_cmd)
                print(f"Started bot instance {instance_index} in screen session: {session_name}")
                print(f"  Attach with: screen -r {session_name}")
                print(f"  Command: {' '.join(screen_cmd)}")


        print(f"Script for instance {instance_index} launched with token: {token[:15]}...{token[-5:]}")
        if disable_stagger_flag:
            print(f"  Instance {instance_index} was launched WITH the -r flag (internal staggering disabled).")

        if not simultaneous_processes and i < num_bots - 1:
            print(f"Waiting {process_launch_delay_s} seconds before launching the next script process...")
            await asyncio.sleep(process_launch_delay_s)

async def main():
    parser = argparse.ArgumentParser(description="Launch Discord selfbots. Post staggering is handled within each bot script unless overridden.")
    parser.add_argument("-s", "--simultaneous", action="store_true",
                       help="Launch all bot script *processes* simultaneously (or very close together).")
    parser.add_argument("-d", "--delay", type=int, default=DEFAULT_PROCESS_LAUNCH_DELAY,
                       help=f"Delay in seconds between launching bot *processes* if not simultaneous (default: {DEFAULT_PROCESS_LAUNCH_DELAY}s). This is NOT the Discord post stagger time.")
    parser.add_argument("--stop", action="store_true", help="Only stop all existing bot instances and exit.")
    parser.add_argument("--restart", action="store_true",
                       help="Stop all existing bot instances and restart them all. Processes will be launched according to -s or -d flags.")
    parser.add_argument("--disable-internal-stagger", action="store_true",
                        help="Pass the '-r' flag to each selfbot script instance, disabling their internal initial post staggering mechanism. Use with caution.")


    args = parser.parse_args()

    if not os.path.exists(SCRIPT_NAME):
        print(f"Error: Target script '{SCRIPT_NAME}' not found in the current directory.")
        print(f"Please ensure '{SCRIPT_NAME}' is present or update the SCRIPT_NAME variable in this launcher.")
        sys.exit(1)

    if args.stop:
        await stop_all_bots()
        print("Stop command processed. Exiting.")
        sys.exit(0)

    if args.restart:
        await stop_all_bots()
        print("Waiting a few seconds for processes to terminate gracefully...")
        await asyncio.sleep(5) # Give some time for processes to die
        print("Restarting bot script processes...")
        # For restart, respect simultaneous/delay flags for process launching.
        # The --disable-internal-stagger flag will also be respected if provided.
        await launch_scripts(simultaneous_processes=args.simultaneous,
                             process_launch_delay_s=args.delay,
                             disable_stagger_flag=args.disable_internal_stagger)
        print(f"All {len(tokens)} bot script processes have been commanded to restart.")
    else:
        await launch_scripts(simultaneous_processes=args.simultaneous,
                             process_launch_delay_s=args.delay,
                             disable_stagger_flag=args.disable_internal_stagger)

        if not args.simultaneous and len(tokens) > 1 :
            valid_tokens_count = sum(1 for t in tokens if not (t.startswith("YOUR_") or len(t) < 50))
            if valid_tokens_count > 1:
                total_process_wait = args.delay * (valid_tokens_count - 1)
                print(f"All script processes for valid tokens launched. Total wait time between process launches was {total_process_wait} seconds.")
        elif args.simultaneous and len(tokens) > 0 and any(not (t.startswith("YOUR_") or len(t) < 50) for t in tokens):
            print("All script processes for valid tokens launched simultaneously (or near so).")
        elif len(tokens) == 1 and not (tokens[0].startswith("YOUR_") or len(tokens[0]) < 50) :
             print("Single script process for valid token launched.")
        elif not any(not (t.startswith("YOUR_") or len(t) < 50) for t in tokens):
             print("No valid tokens were processed. Please check the 'tokens' list in bots.py.")
        else:
            print("No tokens found or processed.")


if __name__ == "__main__":
    # Check for placeholder in tokens list early
    if not tokens or all(token.startswith("YOUR_") for token in tokens):
        print("CRITICAL ERROR: The 'tokens' list in bots.py is empty or only contains placeholders.")
        print("Please edit bots.py and add your actual Discord user tokens.")
        sys.exit(1)
        
    asyncio.run(main())
