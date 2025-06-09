---
# 🚀 Discord Adbot Manager 🚀

**⚠️ WARNING: Running self-bots is strictly against Discord's Terms of Service and will likely lead to permanent account termination. Use this software at your own risk. The developer of this tool is not responsible for any consequences arising from its misuse. ⚠️**

This project, `discord-adbot` by millson1, provides a robust, multi-instance Discord self-bot manager designed to automate posting promotional messages to a target channel and replying to direct messages (DMs) from users. It features shared state management for replied users across all bot instances, staggered initial posting, and per-instance logging.

## ✨ Features ✨

* **Multi-Instance Support**: Run multiple self-bot instances concurrently using different Discord tokens.
* **Centralized DM Tracking**: A shared `replied_users_shared.json` file ensures that only one bot instance replies to a given user's DM, preventing duplicate responses and efficiently managing interactions.
* **Scheduled Posting**: Each bot instance periodically posts messages to a designated channel from a predefined list.
* **Automated DM Replies**: Bots automatically reply to new DMs with a custom message and then block the user.
* **Configurable Delays**: Randomize delays for both channel posting and DM replies to mimic human behavior and reduce the risk of detection.
* **Initial Post Staggering**: Stagger the initial post times of multiple bot instances to avoid all bots posting simultaneously upon startup. This can be enabled or disabled.
* **Per-Instance Logging**: Each bot instance logs its activities to a dedicated file (`selfbot_instance_X.log`) for easier debugging and monitoring, alongside a global manager log (`bot_manager.log`).
* **Legacy Process Stopper**: A utility command (`stop-legacy`) to attempt to terminate old, external bot processes that might be running from previous setups (e.g., in `screen` sessions on Linux or Python processes on Windows).

## 🎬 Getting Started 🎬

### Prerequisites

* Python 3.8+
* `discord.py-self` library (specifically a development version for self-bot functionality)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/millson1/discord-adbot.git
    cd discord-adbot
    ```

2.  **Install the required `discord.py-self` library (developer version):**

    **Crucial Note:** You need a specific "developer" or "self-bot enabled" fork of `discord.py`. The standard `discord.py` library does not support self-bot functionality. You'll typically install it directly from a Git repository.

    To install the `discord.py-self` dev version, follow these steps:

    * **Uninstall any existing `discord.py` or `discord.py-self` installations first:**
        ```bash
        pip uninstall discord.py discord.py-self -y
        ```
    * **Install the dev version from a known self-bot fork (replace with the actual fork URL if different):**
        ```bash
        pip install git+https://github.com/dolfies/discord.py-self@master
        ```
        *(This URL is an example. Please search for the most current and recommended `discord.py-self` fork if this one is outdated.)*

### ⚙️ Configuration ⚙️

All configurable parameters are located at the top of the `main.py` (or your script name) file.

```python
# --- Unified Configuration ---
DEFAULT_TOKENS_LIST = [
    "YOUR_TOKEN_1", # 🔑 Replace with your actual Discord tokens
    "YOUR_TOKEN_2"
]

# For the 'stop-legacy' command, to stop old instances of the separate script
LEGACY_SCRIPT_NAME = "discord_selfbot_script.py" # Name of your old script if you're stopping legacy processes

# --- SelfBotClient Configuration (passed to each instance) ---
TARGET_CHANNEL_ID = 910667265760956478 # 🎯 The ID of the channel where bots will post messages
REPLIED_USERS_FILE = "replied_users_shared.json" # File to store replied user IDs (shared across instances)
POST_INTERVAL_MIN_SECONDS = 7200 # ⏰ Minimum delay between posts (in seconds)
POST_INTERVAL_MAX_SECONDS = 7200 # ⏰ Maximum delay between posts (in seconds)
DM_REPLY_DELAY_MIN_SECONDS = 50 # 💬 Minimum delay before replying to a DM (in seconds)
DM_REPLY_DELAY_MAX_SECONDS = 200 # 💬 Maximum delay before replying to a DM (in seconds)
DM_CHECK_INTERVAL_SECONDS = 60 # 🔎 How often to check for new DMs (in seconds)
MAX_DM_AGE_DAYS = 1 # 🗑️ Ignore DMs older than this many days
DM_REPLY_MESSAGE = "https://discord.gg/5eMRJKg4sB - Join for more Information also!" # ✍️ Your DM reply message

POST_MESSAGES = [
    # Add your various messages here. The bot will pick one randomly.
    """
- Java or Bedrock: __**Java 1.21**__
- Realm/Server/World: **Server**
- Number of players:**10+**
- Length of Play Session: **2h+**
- Gametype:*** Survival, chill, longterm***
- Language: **English**
    """,
    # ... (more messages) ...
]

# Initial post staggering config (applied if not disabled)
INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS = 60 * 60 # 60 minutes
MIN_INITIAL_POST_DELAY_SECONDS = 0 # Base delay for first bot / all bots (if staggering is off)
```

**Key configuration points:**

* **`DEFAULT_TOKENS_LIST`**: Replace the placeholder tokens with your actual Discord user tokens. You can add as many as you need. **Each token represents a separate bot instance.**
* **`TARGET_CHANNEL_ID`**: Set this to the Discord channel ID where you want the bots to post.
* **`DM_REPLY_MESSAGE`**: Customize the message sent in response to DMs.
* **`POST_MESSAGES`**: Populate this list with all the different messages your bots should post.
* Adjust `POST_INTERVAL_MIN_SECONDS`, `POST_INTERVAL_MAX_SECONDS`, `DM_REPLY_DELAY_MIN_SECONDS`, `DM_REPLY_DELAY_MAX_SECONDS`, `DM_CHECK_INTERVAL_SECONDS`, `MAX_DM_AGE_DAYS` to suit your desired behavior and avoid rate limits.
* `INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS` and `MIN_INITIAL_POST_DELAY_SECONDS` control how bots space out their very first posts when they start up.

### ▶️ Running the Bot Manager ▶️

You can run the bot manager using command-line arguments.

#### Start all bots

To start all bot instances defined by your tokens:

```bash
python main.py start
```

**Example with custom tokens and disabled staggering:**

```bash
python main.py start --tokens "token1,token2,token3" --disable-initial-staggering
```

**Example with custom staggering delays:**

```bash
python main.py start --initial-stagger-base-delay 300 --initial-stagger-per-instance 3600
```

#### Stop legacy processes

If you were previously running self-bots using a different script or method (e.g., in `screen` sessions), you can try to stop those processes:

```bash
python main.py stop-legacy
```

You can specify the name of the legacy script if it's different from the default `discord_selfbot_script.py`:

```bash
python main.py stop-legacy --legacy-script-name "my_old_bot.py"
```

### 🧩 Command-line Arguments 🧩

* `--tokens "token1,token2"`: (Optional) Comma-separated list of Discord tokens. If provided, this overrides the `DEFAULT_TOKENS_LIST` in the script.
* `--disable-initial-staggering`: (Optional) A flag to disable the initial delay staggering for bot posts. All bots will attempt their first post after the `initial-stagger-base-delay`.
* `--initial-stagger-base-delay <seconds>`: (Optional) Sets the base delay (in seconds) before the first bot (or all bots if staggering is disabled) makes its initial post. Default is 0.
* `--initial-stagger-per-instance <seconds>`: (Optional) Sets the additional delay (in seconds) added per bot instance for their first post. This creates the "staggering" effect. Default is 3600 (1 hour).
* `--manager-log-file <filename>`: (Optional) Specifies the file to log BotManager specific messages. Default is `bot_manager.log`.
* `start`: Command to start and run the self-bots.
* `stop-legacy`: Command to attempt to stop previously running bot processes.
    * `--legacy-script-name <filename>`: (Optional, used with `stop-legacy`) The filename of the legacy script to target for termination. Default is `discord_selfbot_script.py`.

## 📜 Logging 📜

* **`bot_manager.log`**: Contains logs from the central `BotManager`, including startup, shutdown, and shared state management.
* **`selfbot_instance_X.log`**: Each bot instance creates its own log file (e.g., `selfbot_instance_0.log`, `selfbot_instance_1.log`), detailing its specific actions, DMs received, and posts made.
* Console output will also show relevant messages from both the manager and individual bot instances.

## 🧠 How it Works 🧠

1.  **`main_app()`**: Parses command-line arguments and initializes the `BotManager`.
2.  **`BotManager`**:
    * Loads and saves the `replied_users_shared.json` file, which acts as a global blacklist for users who have already received a DM reply from *any* bot instance.
    * Creates and manages `SelfBotClient` instances, passing them configuration and a reference to itself for shared state management.
3.  **`SelfBotClient` (inherits `discord.Client`)**:
    * Each instance connects to Discord using its provided token.
    * `on_ready()`: Initiates two background tasks: `check_dms_periodically()` and `post_periodically()`.
    * `on_message()`: If a DM is received, it triggers `process_dm()`.
    * `post_periodically()`: Selects a random message from `POST_MESSAGES` and sends it to `TARGET_CHANNEL_ID` at a random interval. Includes initial staggering logic.
    * `check_dms_periodically()`: Iterates through recent DMs. If a new DM is found from a user not in the shared `replied_users` list, it calls `process_dm()`.
    * `process_dm()`:
        * Acquires a per-user lock (local to the instance) to prevent multiple concurrent processing attempts for the same user by *that specific instance*.
        * Checks the global `replied_users` list (via `BotManager`) to see if any bot has already replied.
        * If not replied and DM is within `MAX_DM_AGE_DAYS`, it waits a random `DM_REPLY_DELAY` and sends the `DM_REPLY_MESSAGE`.
        * Upon successful sending, it adds the user's ID to the shared `replied_users` list (via `BotManager`) and attempts to block the user.
    * Handles various Discord API exceptions (Forbidden, HTTPException) with appropriate logging and retry logic.

## 🚨 Important Considerations 🚨

* **Discord ToS**: As stated, using self-bots is against Discord's Terms of Service. Your account is at risk of being banned. Proceed with extreme caution.
* **Rate Limits**: The code includes random delays and some basic retry logic for HTTP errors to mitigate Discord API rate limits, but aggressive usage can still trigger them. Be mindful of the `POST_INTERVAL` and `DM_REPLY_DELAY` settings.
* **Error Handling**: Comprehensive error handling is implemented for network issues, permissions, and other common problems, ensuring the bots are resilient and log critical information.
* **Process Management**: For long-term operation, especially on Linux, consider using tools like `screen`, `tmux`, or `systemd` to keep the Python script running in the background. Note that this project includes a `stop-legacy` command to help manage older, simpler `screen` or `python` processes.
