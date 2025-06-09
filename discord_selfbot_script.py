import os
import asyncio
import sys
import subprocess
import shutil
import argparse
import random
import json
import logging
from datetime import datetime, timedelta, timezone
import discord  # Should be discord.py-self

# --- Unified Configuration ---
DEFAULT_TOKENS_LIST = [
    "token1",
    "token2"
]
# you can add as many as you need

# For the 'stop-legacy' command, to stop old instances of the separate script
LEGACY_SCRIPT_NAME = "discord_selfbot_script.py"

# --- SelfBotClient Configuration (passed to each instance) ---
TARGET_CHANNEL_ID = # ENTER YOUR CHANNEL ID HERE
REPLIED_USERS_FILE = "replied_users_shared.json"  # Single shared file
POST_INTERVAL_MIN_SECONDS = 7200
POST_INTERVAL_MAX_SECONDS = 7200
DM_REPLY_DELAY_MIN_SECONDS = 50
DM_REPLY_DELAY_MAX_SECONDS = 200
DM_CHECK_INTERVAL_SECONDS = 60
MAX_DM_AGE_DAYS = 1
DM_REPLY_MESSAGE = "Your reply"

POST_MESSAGES = [
    """
Message 1
    """,
    """
Hello World!
    """
]

# Initial post staggering config (applied if not disabled)
INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS = 60 * 60  # 60 minutes
MIN_INITIAL_POST_DELAY_SECONDS = 0  # Base delay for first bot / all bots

# --- END OF CONFIG --- #


# --- Global Logger for BotManager and Script ---
manager_logger = logging.getLogger('BotManager')
manager_logger.setLevel(logging.INFO)
console_handler_manager = logging.StreamHandler(sys.stdout)
formatter_manager = logging.Formatter('%(asctime)s [BotManager] [%(levelname)s] %(message)s')
console_handler_manager.setFormatter(formatter_manager)
if not manager_logger.handlers:
    manager_logger.addHandler(console_handler_manager)


# Optional: Add file handler for manager_logger if desired

# --- BotManager Class ---
class BotManager:
    def __init__(self, replied_users_file_path, global_log_file=None):
        self.replied_users_file = replied_users_file_path
        self.replied_users_data = set()
        self.replied_users_lock = asyncio.Lock()
        self.clients = []
        self.client_tasks = []
        self.logger = manager_logger  # Use the global manager_logger

        if global_log_file:
            try:
                file_handler_manager = logging.FileHandler(global_log_file, mode='a', encoding='utf-8')
                file_handler_manager.setFormatter(formatter_manager)
                self.logger.addHandler(file_handler_manager)
                self.logger.info(f"BotManager logging also to {global_log_file}")
            except Exception as e:
                self.logger.error(f"Failed to set up BotManager file log: {e}")

    async def _execute_load_replied_users_sync(self):
        # Assumes lock is held by caller
        # Moved retry logic here
        for attempt in range(3):
            try:
                if os.path.exists(self.replied_users_file):
                    with open(self.replied_users_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.replied_users_data = set(map(str, data)) if isinstance(data, list) else set()
                        self.logger.debug(
                            f"Loaded {len(self.replied_users_data)} replied users from '{self.replied_users_file}' (attempt {attempt + 1})")
                        return
                else:
                    self.replied_users_data = set()
                    self.logger.info(
                        f"Replied users file '{self.replied_users_file}' not found. Starting with empty set. (attempt {attempt + 1})")
                    return
            except (IOError, json.JSONDecodeError) as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/3: Error loading replied users from '{self.replied_users_file}': {e}. Retrying...")
                if attempt < 2:  # Only sleep if not the last attempt
                    await asyncio.sleep(random.uniform(0.2, 0.7))
            except Exception as e:  # Catch any other unexpected error
                self.logger.error(f"Attempt {attempt + 1}/3: Unexpected error loading replied users: {e}",
                                  exc_info=True)
                if attempt < 2:
                    await asyncio.sleep(random.uniform(0.2, 0.7))

        self.logger.error(
            f"Failed to load replied users from '{self.replied_users_file}' after multiple retries. Using empty set.")
        self.replied_users_data = set()

    async def _execute_save_replied_users_sync(self):
        # Assumes lock is held by caller
        # Moved retry logic here
        for attempt in range(3):
            try:
                with open(self.replied_users_file, 'w', encoding='utf-8') as f:
                    json.dump(list(map(str, self.replied_users_data)), f, indent=4)
                self.logger.debug(
                    f"Saved {len(self.replied_users_data)} replied users to '{self.replied_users_file}' (attempt {attempt + 1})")
                return
            except IOError as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/3: Error saving replied users to '{self.replied_users_file}': {e}. Retrying...")
                if attempt < 2:
                    await asyncio.sleep(random.uniform(0.2, 0.7))
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1}/3: Unexpected error saving replied users: {e}", exc_info=True)
                if attempt < 2:
                    await asyncio.sleep(random.uniform(0.2, 0.7))
        self.logger.error(f"Failed to save replied users to '{self.replied_users_file}' after multiple retries.")

    async def load_initial_replied_users(self):
        async with self.replied_users_lock:
            await self._execute_load_replied_users_sync()
        self.logger.info(f"BotManager: Initial load completed. {len(self.replied_users_data)} replied users.")

    async def get_replied_status(self, user_id_str):
        """Checks if user is in the replied list. Acquires lock."""
        async with self.replied_users_lock:
            return user_id_str in self.replied_users_data

    async def commit_replied_user_add(self, user_id_str):
        """Adds user to replied list and saves. Acquires lock. Returns True if added, False if already present."""
        async with self.replied_users_lock:
            if user_id_str not in self.replied_users_data:
                self.replied_users_data.add(user_id_str)
                await self._execute_save_replied_users_sync()
                return True
            return False

    async def start_all_bots(self, tokens, disable_initial_staggering, initial_post_stagger_config):
        await self.load_initial_replied_users()
        self.logger.info(f"Starting {len(tokens)} bot instance(s)...")

        for i, token in enumerate(tokens):
            client_instance = SelfBotClient(
                token=token,
                instance_index=i,
                bot_manager=self,
                disable_staggering_flag=disable_initial_staggering,
                initial_post_stagger_config=initial_post_stagger_config,
                target_channel_id=TARGET_CHANNEL_ID,
                post_messages=POST_MESSAGES,
                post_interval=(POST_INTERVAL_MIN_SECONDS, POST_INTERVAL_MAX_SECONDS),
                dm_reply_delay=(DM_REPLY_DELAY_MIN_SECONDS, DM_REPLY_DELAY_MAX_SECONDS),
                dm_check_interval=DM_CHECK_INTERVAL_SECONDS,
                max_dm_age_days=MAX_DM_AGE_DAYS,
                dm_reply_message=DM_REPLY_MESSAGE
            )
            self.clients.append(client_instance)
            # client.start() is blocking, so we create a task for it
            task = asyncio.create_task(client_instance.start(token), name=f"BotClient-{i}")
            self.client_tasks.append(task)
            self.logger.info(f"Bot instance {i} task created.")

        # Wait for all client.start tasks to complete their initial phase (login)
        # Note: client.start() itself runs the bot's event loop until it's closed.
        # We don't `await` them all here in a way that blocks BotManager from other duties if needed,
        # but we do want to catch immediate startup errors.
        # For now, creating tasks is enough. The main app loop will keep them running.
        self.logger.info("All bot client start tasks have been created.")

    async def stop_all_managed_bots(self):
        self.logger.info("Attempting to stop all managed bot clients...")
        if not self.clients:
            self.logger.info("No clients to stop.")
            return

        stop_client_tasks = []
        for client in self.clients:
            if client and not client.is_closed():
                self.logger.info(f"Requesting close for bot instance {client.instance_index}...")
                stop_client_tasks.append(asyncio.create_task(client.close(), name=f"BotClose-{client.instance_index}"))

        if stop_client_tasks:
            results = await asyncio.gather(*stop_client_tasks, return_exceptions=True)
            for i, res in enumerate(results):
                if isinstance(res, Exception):
                    self.logger.error(f"Error closing client {i}: {res}")  # Index here is from stop_client_tasks
            self.logger.info("All client close commands issued.")
        else:
            self.logger.info("No active clients needed stopping.")

        # Wait for the main client_tasks (from client.start()) to finish
        # This happens naturally if client.close() causes client.start() to return
        if self.client_tasks:
            self.logger.info("Waiting for main client tasks to complete...")
            await asyncio.gather(*self.client_tasks, return_exceptions=True)
            self.logger.info("Main client tasks completed.")

        # Final save of replied users
        async with self.replied_users_lock:
            await self._execute_save_replied_users_sync()
        self.logger.info("Final save of replied users attempted. Bot manager shutdown complete.")


# --- SelfBotClient Class (adapted from original) ---
class SelfBotClient(discord.Client):
    def __init__(self, token, instance_index, bot_manager,
                 disable_staggering_flag, initial_post_stagger_config,
                 target_channel_id, post_messages, post_interval,
                 dm_reply_delay, dm_check_interval, max_dm_age_days, dm_reply_message,
                 **options):
        super().__init__(**options)  # Pass any other discord.Client options
        self.token_value = token  # Store for potential internal use, though start() takes it
        self.instance_index = instance_index
        self.manager = bot_manager  # Reference to BotManager

        self.disable_staggering_flag = disable_staggering_flag
        self.min_initial_post_delay, self.per_instance_stagger = initial_post_stagger_config

        self.target_channel_id = target_channel_id
        self.post_messages = post_messages
        self.post_interval_min, self.post_interval_max = post_interval
        self.dm_reply_delay_min, self.dm_reply_delay_max = dm_reply_delay
        self.dm_check_interval = dm_check_interval
        self.max_dm_age_days = max_dm_age_days
        self.dm_reply_message = dm_reply_message

        self.dm_handling_locks = {}  # Lock per user_id for this specific bot instance

        # --- Per-Instance Logging Setup ---
        self.log_file_name = f"selfbot_instance_{self.instance_index}.log"
        self.logger = logging.getLogger(f'discord_selfbot_inst{self.instance_index}')
        self.logger.setLevel(logging.INFO)

        # Prevent duplicate handlers if this init is somehow called multiple times for the same index (should not happen)
        if not any(isinstance(h, logging.StreamHandler) for h in self.logger.handlers):
            console_handler_instance = logging.StreamHandler(sys.stdout)
            formatter_instance = logging.Formatter(
                f'%(asctime)s [Bot-{self.instance_index}] [%(levelname)s] %(message)s')
            console_handler_instance.setFormatter(formatter_instance)
            self.logger.addHandler(console_handler_instance)

        if not any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            try:
                file_handler_instance = logging.FileHandler(self.log_file_name, mode='a', encoding='utf-8')
                file_handler_instance.setFormatter(formatter_instance)
                self.logger.addHandler(file_handler_instance)
            except Exception as e:
                self.logger.error(f"CRITICAL: Could not set up log file '{self.log_file_name}'. Error: {e}",
                                  exc_info=True)
        self.logger.info(
            f"Instance {self.instance_index} logger initialized. Logging to console and {self.log_file_name}")

    async def on_ready(self):
        if self.user is None:
            self.logger.error("Failed to log in, self.user is None. Check token.")
            await self.close()  # Attempt to gracefully close this specific client
            return

        self.logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        self.logger.warning("############################################################")
        self.logger.warning("### WARNING: RUNNING SELF-BOT! VIOLATES DISCORD ToS!     ###")
        self.logger.warning("### YOUR ACCOUNT IS AT RISK OF PERMANENT SUSPENSION!     ###")
        self.logger.warning("### Auto-blocking users is also a risky automation.      ###")
        self.logger.warning("############################################################")

        # These tasks are managed by the client's own event loop, started by client.start()
        self.loop.create_task(self.check_dms_periodically(), name=f"DMCheck-{self.instance_index}")
        self.loop.create_task(self.post_periodically(), name=f"PostTask-{self.instance_index}")
        self.logger.info("DM check and periodic posting tasks created for this instance.")

    async def on_message(self, message):
        if message.author == self.user:  # Ignore self messages
            return
        if isinstance(message.channel, discord.DMChannel):
            self.logger.debug(f"Received DM via on_message from {message.author} ({message.author.id})")
            # Offload to process_dm, which handles its own locking and manager interaction
            asyncio.create_task(self.process_dm(message), name=f"ProcessDM-{message.author.id}-{self.instance_index}")

    async def post_periodically(self):
        await self.wait_until_ready()
        if self.user is None: return  # Not logged in

        initial_sleep_duration: int
        if self.disable_staggering_flag:
            initial_sleep_duration = self.min_initial_post_delay
            delay_reason = "staggering DISABLED by flag"
        else:
            stagger_component = self.instance_index * self.per_instance_stagger
            initial_sleep_duration = self.min_initial_post_delay + stagger_component
            delay_reason = "staggering ENABLED"

        self.logger.info(
            f"Initial post delay logic: {delay_reason}. Base: {self.min_initial_post_delay}s, Stagger/Inst: {self.per_instance_stagger}s. Calculated total: {initial_sleep_duration}s.")

        if initial_sleep_duration > 0:
            self.logger.info(
                f"Sleeping for {initial_sleep_duration // 60}m {initial_sleep_duration % 60}s before first post.")
            await asyncio.sleep(initial_sleep_duration)

        self.logger.info("Periodic message posting task started (after initial delay/stagger if any).")
        while not self.is_closed():
            try:
                channel = self.get_channel(self.target_channel_id)
                if channel and isinstance(channel, discord.TextChannel):  # Ensure it's a text channel
                    chosen_message = random.choice(self.post_messages)
                    await channel.send(chosen_message)
                    self.logger.info(f"Posted message in #{channel.name} ({channel.id})")
                elif channel:
                    self.logger.warning(
                        f"Channel {self.target_channel_id} found, but it's not a TextChannel (Type: {type(channel)}). Cannot post.")
                else:
                    self.logger.warning(
                        f"Target channel {self.target_channel_id} not found! Check ID and bot's access.")

                sleep_time = random.randint(self.post_interval_min, self.post_interval_max)
                self.logger.info(
                    f"Next post scheduled in {sleep_time / 60:.2f} minutes (approx. {sleep_time // 3600}h {(sleep_time % 3600) // 60}m).")
                await asyncio.sleep(sleep_time)
            except discord.Forbidden:
                self.logger.error(f"Permission error posting to channel {self.target_channel_id}. Check permissions.",
                                  exc_info=False)  # Don't need full exc for Forbidden
                await asyncio.sleep(300)  # Wait longer if forbidden
            except discord.HTTPException as e:
                self.logger.error(f"HTTP error posting message: {e.status} {getattr(e, 'text', 'No text')}",
                                  exc_info=True)
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                self.logger.info("Post task cancelled.")
                break
            except Exception:
                self.logger.error("Unexpected error in posting task:", exc_info=True)
                await asyncio.sleep(60)  # Wait a bit before retrying loop

    async def check_dms_periodically(self):
        await self.wait_until_ready()
        if self.user is None: return  # Not logged in

        self.logger.info("Periodic DM check task started.")
        while not self.is_closed():
            try:
                self.logger.debug("Running periodic DM check...")
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.max_dm_age_days)

                # Iterate over a copy of private_channels in case it's modified during iteration
                current_private_channels = list(self.private_channels)
                self.logger.debug(f"Checking {len(current_private_channels)} cached private channels.")

                for channel_idx, channel in enumerate(current_private_channels):
                    if self.is_closed(): break  # Stop if bot is closing
                    if isinstance(channel, discord.DMChannel) and channel.recipient:  # Ensure recipient exists
                        recipient_name = getattr(channel.recipient, 'name',
                                                 f'Unknown Recipient ID {getattr(channel.recipient, "id", "N/A")}')
                        try:
                            # Small sleep to avoid hitting rate limits if there are many DM channels
                            if channel_idx > 0 and channel_idx % 10 == 0: await asyncio.sleep(random.uniform(0.3, 0.8))

                            async for message in channel.history(limit=5, after=cutoff_time,
                                                                 oldest_first=False):  # Check a few recent DMs
                                if message.author != self.user:  # Message from other person
                                    user_id_str = str(message.author.id)

                                    # Check with manager if user has already been replied to by ANY instance
                                    if not await self.manager.get_replied_status(user_id_str):
                                        self.logger.info(
                                            f"[Periodic Check] Found potential unreplied DM from {message.author} ({user_id_str}) in DM with {recipient_name}. Processing via process_dm.")
                                        # Offload to process_dm which handles all logic including locks
                                        asyncio.create_task(self.process_dm(message),
                                                            name=f"PeriodicProcessDM-{user_id_str}-{self.instance_index}")
                                    else:
                                        self.logger.debug(
                                            f"[Periodic Check] DM from {message.author} ({user_id_str}) already in SHARED replied list. Skipping.")
                                    break  # Found the latest message from the other user in this DM channel, move to next channel
                        except discord.Forbidden:
                            self.logger.warning(
                                f"[Periodic Check] Cannot read history for DM with {recipient_name} ({channel.id}) - Permission Error.")
                        except discord.HTTPException as e:
                            self.logger.warning(
                                f"[Periodic Check] HTTP error reading history for DM with {recipient_name} ({channel.id}): {e.status}")
                        except Exception:  # Catchall for safety per channel
                            self.logger.error(
                                f"[Periodic Check] Unexpected error reading history for DM with {recipient_name} ({channel.id}):",
                                exc_info=True)

                self.logger.debug(f"Periodic DM check finished. Sleeping for {self.dm_check_interval}s.")
                await asyncio.sleep(self.dm_check_interval)
            except asyncio.CancelledError:
                self.logger.info("DM check task cancelled.")
                break
            except Exception:  # Catchall for the outer loop
                self.logger.error("Unexpected error in periodic DM check task outer loop:", exc_info=True)
                # Shorter sleep on error to retry sooner, but not too short
                await asyncio.sleep(self.dm_check_interval / 2 if self.dm_check_interval > 20 else 10)

    async def on_resumed(self):
        self.logger.info("EVENT: Gateway session has been RESUMED successfully.")
        self.logger.debug(f"DEBUG: Number of private_channels after resume: {len(self.private_channels)}")

    async def process_dm(self, message: discord.Message):
        author = message.author
        if not isinstance(author, discord.User):
            self.logger.warning(
                f"DM author is not a discord.User object (Type: {type(author)}). Cannot process. Author: {author}")
            return

        user_id_str = str(author.id)

        # --- Instance-specific lock: Prevents this bot instance from processing multiple DMs from same user concurrently ---
        if user_id_str not in self.dm_handling_locks:
            self.dm_handling_locks[user_id_str] = asyncio.Lock()

        dm_processing_lock = self.dm_handling_locks[user_id_str]
        if dm_processing_lock.locked():
            self.logger.debug(
                f"DM processing for {user_id_str} is already in progress by this instance. Skipping duplicate call.")
            return

        async with dm_processing_lock:
            # --- Check Phase (with global replied list from BotManager) ---
            if await self.manager.get_replied_status(user_id_str):
                self.logger.info(
                    f"User {author} ({user_id_str}) is ALREADY in SHARED replied list (checked before send). Skipping.")
                # Clean up lock if no longer needed (though it might be reused if user DMs again quickly)
                # Consider if self.dm_handling_locks should be cleaned up more aggressively or not. For now, let it persist.
                return

            # --- DM Validation (age, etc.) ---
            now_utc = datetime.now(timezone.utc)
            message_created_at_utc = message.created_at.astimezone(
                timezone.utc) if message.created_at.tzinfo else message.created_at.replace(tzinfo=timezone.utc)
            message_age = now_utc - message_created_at_utc

            if message_age > timedelta(days=self.max_dm_age_days):
                self.logger.info(
                    f"DM from {author} ({user_id_str}) is too old ({message_age.days}d {message_age.seconds // 3600}h). Skipping.")
                return

            msg_preview = f"'{message.content[:50].replace(chr(10), ' ')}...'" if message.content else "[Content Unavailable/Empty]"
            self.logger.info(
                f"User {author} ({user_id_str}) NOT in SHARED replied users. Processing new DM. Message: {msg_preview}")

            # --- Send Phase (no global lock held here) ---
            reply_delay = random.randint(self.dm_reply_delay_min, self.dm_reply_delay_max)
            self.logger.info(f"Waiting {reply_delay} seconds before replying to {author} ({user_id_str}).")
            await asyncio.sleep(reply_delay)

            sent_successfully = False
            max_send_retries = 2
            send_retry_delay_base = 5

            for attempt in range(max_send_retries + 1):  # 0, 1, 2
                if self.is_closed():
                    self.logger.warning(f"Bot instance closing, aborting DM send to {user_id_str}.")
                    break
                try:
                    await message.channel.send(self.dm_reply_message)
                    self.logger.info(f"Successfully sent DM reply to {author} ({user_id_str}).")
                    sent_successfully = True
                    break
                except discord.Forbidden:
                    self.logger.error(
                        f"CANNOT SEND DM (FORBIDDEN) to {author} ({user_id_str}). Not retrying for this user by this instance.",
                        exc_info=False)
                    break  # No point retrying if forbidden
                except discord.HTTPException as e:
                    log_level = logging.WARNING if attempt < max_send_retries else logging.ERROR
                    self.logger.log(log_level,
                                    f"HTTP error {e.status} sending DM to {author} ({user_id_str}) (Attempt {attempt + 1}/{max_send_retries + 1}). Text: {getattr(e, 'text', 'N/A')}",
                                    exc_info=False)
                    if 500 <= e.status < 600:  # Server-side errors, retry
                        if attempt < max_send_retries: await asyncio.sleep(send_retry_delay_base * (2 ** attempt))
                    elif e.status == 429:  # Rate limited
                        retry_after = float(
                            e.response.headers.get('Retry-After', send_retry_delay_base * (2 ** attempt))) if hasattr(e,
                                                                                                                      'response') and e.response else (
                                    send_retry_delay_base * (2 ** attempt))
                        self.logger.warning(
                            f"Rate limited sending DM. Discord suggests waiting {retry_after:.2f}s. Will retry if attempts left or wait and break.")
                        if attempt < max_send_retries:
                            await asyncio.sleep(retry_after)
                        else:
                            break  # Exhausted retries for rate limit
                    else:  # Other HTTP errors (e.g., 400, 403 already handled by Forbidden) - likely not retryable
                        break
                except Exception as e:  # Catch any other unexpected error during send
                    log_level = logging.WARNING if attempt < max_send_retries else logging.ERROR
                    self.logger.log(log_level,
                                    f"Unexpected error sending DM to {author} ({user_id_str}) (Attempt {attempt + 1}/{max_send_retries + 1}).",
                                    exc_info=True)
                    if attempt < max_send_retries: await asyncio.sleep(send_retry_delay_base * (2 ** attempt))

            # --- Post-Send Update Phase (interact with BotManager for shared state) ---
            if sent_successfully:
                added_by_this_op = await self.manager.commit_replied_user_add(user_id_str)
                if added_by_this_op:
                    self.logger.info(
                        f"Added {author} ({user_id_str}) to SHARED replied list by this instance. Total in manager: {len(self.manager.replied_users_data)}")
                    # Block user
                    try:
                        self.logger.info(f"Attempting to block user {author} ({user_id_str})...")
                        await author.block()
                        self.logger.info(f"Successfully blocked user {author} ({user_id_str}).")
                    except discord.Forbidden:
                        self.logger.error(f"Failed to block user {author} ({user_id_str}) - Forbidden.", exc_info=False)
                    except discord.HTTPException as e_block:
                        self.logger.error(
                            f"Failed to block user {author} ({user_id_str}) - HTTP Exception {e_block.status}.",
                            exc_info=False)
                    except Exception as e_block_unexpected:
                        self.logger.error(f"Unexpected error blocking user {author} ({user_id_str}).", exc_info=True)
                else:
                    self.logger.info(
                        f"User {author} ({user_id_str}) was already in SHARED replied list or added concurrently. This instance won't re-add.")
            else:
                self.logger.warning(
                    f"Ultimately FAILED to send DM reply to {author} ({user_id_str}). User not added to replied list by this instance.")
        # Instance-specific lock for this user is now released.
        # Consider if self.dm_handling_locks[user_id_str] should be deleted here or kept for a while.
        # If deleted: del self.dm_handling_locks[user_id_str] (but needs try-except if multiple tasks somehow try to del)


# --- Legacy Process Stopper (from original launcher) ---
async def stop_legacy_bot_processes(script_name_to_stop):
    manager_logger.info(
        f"Attempting to stop all existing legacy bot instances running script: {script_name_to_stop}...")
    stopped_count = 0  # For screen sessions primarily

    if sys.platform == "win32":
        cmd_python = [
            "wmic", "process", "where",
            f"caption='python.exe' and commandline like '%{script_name_to_stop}%'",
            "delete"
        ]
        cmd_pythonw = [
            "wmic", "process", "where",
            f"caption='pythonw.exe' and commandline like '%{script_name_to_stop}%'",
            "delete"
        ]
        try:
            # Use asyncio.to_thread for subprocess.run if we want this to be non-blocking for manager
            # For a one-off command, synchronous might be fine.
            await asyncio.to_thread(subprocess.run, cmd_python, capture_output=True, text=True, check=False)
            await asyncio.to_thread(subprocess.run, cmd_pythonw, capture_output=True, text=True, check=False)
            manager_logger.info("Sent termination signal to legacy Python processes on Windows.")
        except FileNotFoundError:
            manager_logger.error("WMIC command not found. Cannot stop legacy processes on Windows automatically.")
        except subprocess.CalledProcessError as e:
            manager_logger.error(f"Error stopping legacy processes on Windows: {e}")
    else:  # Linux or macOS
        screen_path = shutil.which("screen")
        if screen_path:
            manager_logger.info("Attempting to stop legacy screen sessions...")
            # Assuming legacy screen sessions might be named differently or we just try a range
            for i in range(1, 20):  # Try a range of potential legacy screen names
                session_name = f"discord-bot-{i}"  # Example legacy naming
                screen_quit_cmd = ["screen", "-S", session_name, "-X", "quit"]
                result = await asyncio.to_thread(subprocess.run, screen_quit_cmd, capture_output=True, text=True)
                if "No screen session found" not in result.stderr and result.returncode == 0:
                    manager_logger.info(f"Successfully sent quit command to legacy screen session: {session_name}")
                    stopped_count += 1
                elif "No screen session found" not in result.stderr and result.stderr:
                    manager_logger.warning(f"Screen quit for {session_name} stderr: {result.stderr.strip()}")

        manager_logger.info(f"Attempting to pkill legacy processes matching 'python(3) .*{script_name_to_stop}.*'")
        pkill_patterns = [
            f"python3 .*{script_name_to_stop}.*",
            f"python .*{script_name_to_stop}.*"
        ]
        killed_by_pkill = False
        for pattern in pkill_patterns:
            cmd = ["pkill", "-f", pattern]
            try:
                result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)
                if result.returncode == 0:  # pkill returns 0 if any process was signalled
                    manager_logger.info(f"pkill command '{' '.join(cmd)}' successful (may have killed processes).")
                    killed_by_pkill = True
                elif result.returncode == 1:  # No processes matched
                    manager_logger.info(f"pkill command '{' '.join(cmd)}' found no matching processes.")
                else:  # Other error
                    manager_logger.warning(
                        f"pkill command '{' '.join(cmd)}' failed. RC: {result.returncode}, stderr: {result.stderr.strip()}")

            except FileNotFoundError:
                manager_logger.error(f"Command 'pkill' not found. Cannot pkill legacy processes.")
                break
        if killed_by_pkill:
            manager_logger.info("pkill attempted to terminate matching legacy processes.")

    if stopped_count > 0:
        manager_logger.info(f"Stopped {stopped_count} legacy screen session(s).")
    manager_logger.info("Finished attempt to stop existing legacy bots.")


# --- Main Application ---
async def main_app():
    parser = argparse.ArgumentParser(
        description="Unified Discord Self-Bot Manager. Manages multiple bot instances in one script.")
    parser.add_argument(
        "--tokens",
        type=str,
        default=None,  # If None, uses DEFAULT_TOKENS_LIST
        help=f"Comma-separated list of Discord tokens. Overrides the hardcoded list. Example: \"token1,token2\""
    )
    parser.add_argument(
        "--disable-initial-staggering",
        action="store_true",
        help="Disable initial post staggering for all bot instances."
    )
    parser.add_argument(
        "--initial-stagger-base-delay", type=int, default=MIN_INITIAL_POST_DELAY_SECONDS,
        help=f"Base delay in seconds before the first bot posts (or for all if staggering per instance is 0). Default: {MIN_INITIAL_POST_DELAY_SECONDS}s"
    )
    parser.add_argument(
        "--initial-stagger-per-instance", type=int, default=INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS,
        help=f"Additional delay in seconds per bot instance for their first post. Default: {INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS}s"
    )
    parser.add_argument(
        "--manager-log-file", type=str, default="bot_manager.log",
        help="File to log BotManager specific messages. Default: bot_manager.log"
    )

    # Subparsers for commands like 'start' and 'stop-legacy'
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Start command
    parser_start = subparsers.add_parser("start", help="Start and run the self-bots.")
    # parser_start can have its own specific arguments in the future if needed

    # Stop-legacy command
    parser_stop_legacy = subparsers.add_parser("stop-legacy",
                                               help="Attempt to stop old, externally running bot processes (uses pkill/wmic).")
    parser_stop_legacy.add_argument(
        "--legacy-script-name", type=str, default=LEGACY_SCRIPT_NAME,
        help=f"Filename of the legacy script to target for stopping. Default: {LEGACY_SCRIPT_NAME}"
    )

    args = parser.parse_args()

    # Process tokens
    tokens_to_use = DEFAULT_TOKENS_LIST
    if args.tokens:
        tokens_to_use = [token.strip() for token in args.tokens.split(',') if token.strip()]
        manager_logger.info(f"Using tokens provided via --tokens argument: {len(tokens_to_use)} tokens.")
    else:
        manager_logger.info(f"Using default hardcoded tokens list: {len(tokens_to_use)} tokens.")

    if not tokens_to_use:
        manager_logger.error("No tokens provided or found in default list. Exiting.")
        sys.exit(1)

    initial_post_stagger_config = (args.initial_stagger_base_delay, args.initial_stagger_per_instance)

    bot_manager = BotManager(replied_users_file_path=REPLIED_USERS_FILE, global_log_file=args.manager_log_file)

    if args.command == "start":
        manager_logger.info("Starting bot manager and all bot instances...")
        if args.disable_initial_staggering:
            manager_logger.info("Initial post staggering is DISABLED via command line flag.")

        try:
            await bot_manager.start_all_bots(
                tokens=tokens_to_use,
                disable_initial_staggering=args.disable_initial_staggering,
                initial_post_stagger_config=initial_post_stagger_config
            )
            # Keep the main script alive while clients are running.
            # asyncio.gather on client_tasks will effectively do this if they run indefinitely.
            if bot_manager.client_tasks:
                manager_logger.info("Bot manager started. Bots are running. Press Ctrl+C to stop.")
                await asyncio.gather(*bot_manager.client_tasks,
                                     return_exceptions=True)  # This will wait for all bots to finish
            else:
                manager_logger.warning("No client tasks were successfully started by BotManager.")

        except KeyboardInterrupt:
            manager_logger.info("KeyboardInterrupt received. Shutting down...")
        except Exception as e:
            manager_logger.critical(f"An unexpected error occurred in main_app: {e}", exc_info=True)
        finally:
            manager_logger.info("Initiating shutdown of BotManager and all managed bots...")
            await bot_manager.stop_all_managed_bots()
            manager_logger.info("Shutdown complete. Exiting.")

    elif args.command == "stop-legacy":
        manager_logger.info(f"Executing 'stop-legacy' command for script name: {args.legacy_script_name}")
        await stop_legacy_bot_processes(args.legacy_script_name)
        manager_logger.info("'stop-legacy' command finished.")


if __name__ == "__main__":
    # Basic check for legacy script if stop-legacy might be used, though not strictly necessary for start
    # if not os.path.exists(LEGACY_SCRIPT_NAME) and "stop-legacy" in sys.argv: # Simple check
    #     manager_logger.warning(f"Legacy script '{LEGACY_SCRIPT_NAME}' not found in current directory. 'stop-legacy' might not be effective if path is different.")

    asyncio.run(main_app())
