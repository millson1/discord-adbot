# 💬 discord-adbot (Multi-Instance Selfbot System)

A **Discord selfbot** system designed to use multiple tokens for posting messages in specified channels (e.g., LFG servers) and automatically replying to Direct Messages (DMs). DM replies are sent only once per user, tracked across all bot instances via a shared file, and users are blocked after a successful DM reply.

> ⚠️ **Disclaimer**  
> Automating user accounts (selfbots) is strictly against [Discord’s Terms of Service](https://discord.com/terms). This project is for **educational use only**. Use it at your own risk — you are solely responsible for any consequences, including account suspension or termination.

---

## ✨ Features

-   **Multi-Token Operation**: Manages and runs multiple Discord user accounts simultaneously.
-   **Automated DM Replies**:
    -   Sends a configurable reply to new DMs.
    -   **Shared Replied User Tracking**: Ensures each unique user receives a DM reply only once, even if they message different bots in the system (uses a shared `replied_users.json`).
    -   **Automatic User Blocking**: Blocks users after successfully replying to their DM.
-   **Configurable Posting Behavior**:
    -   **Initial Post Staggering**: Each bot instance can delay its *first* post by a configurable, incremental amount, ideal for respecting channel cooldowns when starting multiple bots. This can be disabled per instance.
    -   **Regular Post Intervals**: Configurable minimum and maximum time between subsequent posts for each bot.
    -   Customizable list of messages to cycle through.
-   **Robust Operation**:
    -   **Individual Logging**: Each bot instance logs its activity to a separate file (e.g., `selfbot_instance_0.log`).
    -   **Launcher Script (`bots.py`)**:
        -   Easily start, stop, and restart all bot instances.
        -   Supports sequential or simultaneous launching of bot processes.
        -   Cross-platform (Windows, Linux, macOS).
        -   Optional use of `screen` for persistent sessions on Linux/macOS.
-   **Graceful Error Handling**: Attempts to handle common Discord API errors and network issues.

---

## 🛠️ Setup Instructions

### 1. Install Python
Ensure you have Python 3.7+ installed (Python 3.12 is recommended).
[Download Python here](https://www.python.org/downloads/)

---

### 2. Install Dependencies
The main dependency is a specific version of `discord.py` that supports selfbots.

```bash
# Clone the discord.py-self repository
git clone https://github.com/dolfies/discord.py-self
cd discord.py-self

# Install it (use python or python3, and pip or pip3 as appropriate for your system)
python -m pip install -U .[voice]

# Navigate back to your main project directory
cd ..
```
*Note: `asyncio` is a built-in Python library and does not need separate installation via pip.*

---

### 3. Clone This Repo

```bash
git clone https://github.com/your-username/your-repo-name # Replace with your actual repo URL
cd your-repo-name # Replace with your actual repo folder name
```

---

## 🔧 Configuration

Configuration is split between the main selfbot script (`discord_selfbot_script.py`) and the launcher script (`bots.py`).

### A) `discord_selfbot_script.py` (The Selfbot Script)

This script contains the core logic for a single bot instance. It is typically launched by `bots.py` for each token.

Key variables to configure within `discord_selfbot_script.py`:

*   **`DISABLE_STAGGERING` (Line ~12, typically controlled by command-line arg)**:
    *   Set to `True` if the `-r` command-line argument is passed to this script, disabling the initial post stagger for this specific instance.
*   **`INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS` (Line ~16)**:
    *   Default: `30 * 60` (30 minutes)
    *   The delay *between* each bot's *first* post. If bot 0 posts at T, bot 1 will post at T + this value, bot 2 at T + 2 * this value, and so on. This helps respect channel-wide cooldowns when starting many bots.
*   **`MIN_INITIAL_POST_DELAY_SECONDS` (Line ~19)**:
    *   Default: `0`
    *   A small base delay for the very first bot (index 0) or added to all instances if staggering is disabled.
*   **`TARGET_CHANNEL_ID` (Line ~33)**:
    *   Example: `123456789012345678`
    *   The ID of the Discord channel where messages will be posted.
*   **`REPLIED_USERS_FILE` (Line ~35)**:
    *   Default: `"replied_users.json"`
    *   The name of the JSON file used to store IDs of users already replied to. This file is **shared by all instances**.
*   **`POST_INTERVAL_MIN_SECONDS` (Line ~36)** & **`POST_INTERVAL_MAX_SECONDS` (Line ~37)**:
    *   Defaults: `7200` (2 hours) for both.
    *   Minimum and maximum time (in seconds) a bot will wait after posting a message before posting the next one. A random duration between these values is chosen.
*   **`DM_REPLY_DELAY_MIN_SECONDS` (Line ~38)** & **`DM_REPLY_DELAY_MAX_SECONDS` (Line ~39)**:
    *   Defaults: `50` and `200` seconds.
    *   Minimum and maximum delay before replying to a received DM.
*   **`DM_CHECK_INTERVAL_SECONDS` (Line ~40)**:
    *   Default: `60` seconds.
    *   How often the bot periodically checks for DMs (as a backup to the live event).
*   **`MAX_DM_AGE_DAYS` (Line ~41)**:
    *   Default: `1` day.
    *   Only reply to DMs newer than this age.
*   **`DM_REPLY_MESSAGE` (Line ~42)**:
    *   Example: `"Hello! Thanks for your message. Check out our community: https://discord.gg/YOUR_INVITE"`
    *   The message content to send as an automatic DM reply.
*   **`POST_MESSAGES` (List, starting Line ~45)**:
    *   A list of messages the bot will cycle through when posting in `TARGET_CHANNEL_ID`.
    *   Example:
        ```python
        POST_MESSAGES = [
            "Message template 1: Looking for group!",
            "Message template 2: Join our awesome server!",
            # Add more messages here
        ]
        ```
*   **`LOG_FILE_NAME` (Line ~80, dynamically set)**:
    *   Generates unique log files like `selfbot_instance_0.log`, `selfbot_instance_1.log`, etc.

### B) `bots.py` (The Launcher Script)

This script is used to manage and launch multiple instances of `discord_selfbot_script.py`, one for each token you provide.

Key configurations/aspects of `bots.py`:

*   **`tokens` (List, Line ~6)**:
    *   Add your Discord user tokens to this list.
    *   **Placeholder Example**:
        ```python
        tokens = [
            "YOUR_TOKEN_1_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "YOUR_TOKEN_2_YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY",
            "YOUR_TOKEN_3_ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
        ]
        ```
*   **`SCRIPT_NAME` (Line ~11)**:
    *   Default: `"discord_selfbot_script.py"`
    *   The filename of the main selfbot script. Change this if you rename `discord_selfbot_script.py`.
*   **`DEFAULT_PROCESS_LAUNCH_DELAY` (Line ~9)**:
    *   Default: `5` seconds.
    *   Used if launching processes sequentially (see `-d` argument below). This is the delay between starting each *script process*, not the Discord message posting stagger (which is handled internally by `discord_selfbot_script.py`).

---

## 🚀 Running the Bots

It is highly recommended to use `bots.py` to manage your selfbot instances.

Open your terminal or command prompt in the project directory.

**1. Launching Bots:**

*   **To launch all bots sequentially (default, recommended for system stability at startup):**
    ```bash
    python bots.py
    ```
    This will launch each bot process with a `DEFAULT_PROCESS_LAUNCH_DELAY` (e.g., 5 seconds) between them. The *actual posting stagger* is then controlled by `INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS` within each bot.

*   **To launch all bot processes simultaneously:**
    ```bash
    python bots.py -s
    # OR
    python bots.py --simultaneous
    ```
    This starts all script processes at nearly the same time. The internal initial post staggering in `discord_selfbot_script.py` will still apply unless disabled.

*   **To specify a custom delay between launching script processes (if not simultaneous):**
    ```bash
    python bots.py -d 10
    # OR
    python bots.py --delay 10
    ```
    This will wait 10 seconds between launching each bot's script process.

**2. Restarting Bots:**

*   **To stop all running bot instances and restart them (processes launched simultaneously):**
    ```bash
    python bots.py -r
    # OR
    python bots.py --restart
    ```
    This first attempts to terminate any existing bot processes run by this system and then launches them all anew. The restarted selfbot instances will use their default initial post staggering.

**3. How Initial Post Staggering Works:**

*   Each instance of `discord_selfbot_script.py` is assigned an `INSTANCE_INDEX` (0, 1, 2, ...) by `bots.py`.
*   The first post from instance `X` will be delayed by `MIN_INITIAL_POST_DELAY_SECONDS + (X * INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS)`.
*   Example: If `INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS = 1800` (30 minutes) and `MIN_INITIAL_POST_DELAY_SECONDS = 0`:
    *   Bot 0 posts almost immediately.
    *   Bot 1 posts ~30 minutes after Bot 0.
    *   Bot 2 posts ~30 minutes after Bot 1 (i.e., ~60 minutes after Bot 0).
*   This staggering is useful for channels with strict posting cooldowns (e.g., post once every 2 hours). You can set `INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS` to `ChannelCooldown / NumberOfTokens`.

**4. Disabling Initial Post Staggering for Individual Instances (Manual Launch):**

If you were to run `discord_selfbot_script.py` manually (for testing a single instance), you can disable its initial post staggering using the `-r` flag:

```bash
python discord_selfbot_script.py "YOUR_TOKEN" 0 -r
```

This `-r` flag for `discord_selfbot_script.py` is *different* from the `-r`/`--restart` flag for `bots.py`.
Currently, `bots.py` does not automatically pass this `-r` flag to the child scripts. If you want all bots launched by `bots.py` to have their *initial post staggering disabled*, you would need to modify `bots.py` to include the `"-r"` argument when it constructs the command to run `discord_selfbot_script.py`. For example, in `bots.py` within the `launch_scripts` function:
    ```python
    # For Linux/macOS:
    # script_args = [SCRIPT_NAME, token, str(instance_index)] # Original
    script_args = [SCRIPT_NAME, token, str(instance_index), "-r"] # Modified to disable staggering

    # For Windows:
    # command = f"start \"DiscordBotInst{instance_index}\" /B python {SCRIPT_NAME} \"{token}\" {instance_index}" # Original
    command = f"start \"DiscordBotInst{instance_index}\" /B python {SCRIPT_NAME} \"{token}\" {instance_index} -r" # Modified
    ```

**Platform Notes:**
-   On Windows: Bots are launched in new background console windows.
-   On Linux/macOS: Uses `screen` if available (creating sessions like `discord-bot-0`, `discord-bot-1`). You can attach using `screen -r discord-bot-0`. If `screen` is not found, it uses detached subprocesses.

---

## 📌 Important Notes

-   **Shared `replied_users.json`**: All bot instances read from and write to the same `replied_users.json` file. Ensure file permissions allow this if running bots under different users (not typical for this setup).
-   **Log Files**: Check `selfbot_instance_X.log` files for detailed activity and errors for each bot.
-   **Resource Usage**: Running many selfbots can be resource-intensive. Monitor your system.
-   **Rate Limits**: While the script has delays, aggressive use across many tokens can still lead to rate limits or other actions from Discord.
-   **Account Safety**: Selfbots are inherently risky. Use throwaway accounts that you are prepared to lose. Do not use your main Discord account.

---

## 📞 Support / Questions

This project is provided as-is for educational purposes. For bugs or feature suggestions related to the script's functionality, you can open an Issue on the GitHub repository. Community support may be available, but there are no guarantees.

---

## 🧪 Educational Purpose Only

This repository and its contents are intended strictly for educational purposes to demonstrate automation concepts with Python and the Discord API (unofficially). Misuse of this code, such as for spamming or violating Discord's ToS, is strongly discouraged and can lead to severe penalties, including permanent account bans. The user assumes all responsibility for their actions.
```
