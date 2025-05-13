### DANGER ZONE: SELF-BOT CODE USING discord.py-self ###
# Running this code violates Discord's Terms of Service and can lead to
# your account being permanently banned. Use at your own extreme risk.
# This version uses `import discord` as expected by many discord.py-self forks
# and operates without explicit Intents, relying on the fork's handling.

import os
os.environ["DISCORD_PY_USE_AIOHTTP"] = "1" # May still be needed depending on the fork/setup

import discord # Use the standard import name
import sys
import random
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone # Use timezone-aware datetimes

# --- Configuration ---
if len(sys.argv) != 2:
    print("Usage: python discord_selfbot_script.py <your_user_token>")
    print("WARNING: Using your user token for automation violates Discord ToS.")
    sys.exit(1)

TOKEN = sys.argv[1]
TARGET_CHANNEL_ID = 1234567891011121415 # Channel to post messages in
REPLIED_USERS_FILE = "replied_users.json" # File to store IDs of users already replied to
POST_INTERVAL_MIN_SECONDS = 7200 # Minimum time between posts (2 hours)
POST_INTERVAL_MAX_SECONDS = 7400 # Maximum time between posts (~2 hours 3 mins)
DM_REPLY_DELAY_MIN_SECONDS = 50   # Min seconds before replying to a DM
DM_REPLY_DELAY_MAX_SECONDS = 200  # Max seconds before replying to a DM
DM_CHECK_INTERVAL_SECONDS = 60  # How often to periodically check DMs (backup)
MAX_DM_AGE_DAYS = 1             # Only reply to DMs newer than this
DM_REPLY_MESSAGE = "EDIT THIS DM REPLY MESSAGE PLEASE THANKS" # Message to send in reply

# --- Messages to Post ---
POST_MESSAGES = [
    """
PLACEHOLDER MESSAGE
    """,
    """
PLACEHOLDER ONCE AGAIN
    """


]

# --- Logging Setup ---
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(log_formatter)
logger = logging.getLogger('discord_selfbot')
logger.setLevel(logging.INFO) # Set to INFO to see the new messages
logger.addHandler(log_handler)

# --- Self-Bot Class ---
# Initialize Client without explicit intents - relying on discord.py-self defaults
class SelfBotClient(discord.Client):
    def __init__(self, **options):
        # Call super().__init__ without intents
        super().__init__(**options)
        logger.info("Bot initializing using discord.py-self (no explicit intents)...")
        self.replied_users = self._load_replied_users() # Initial load
        logger.info(f"Initially loaded {len(self.replied_users)} replied user IDs from '{REPLIED_USERS_FILE}'")
        self.dm_handling_locks = {} # To prevent race conditions for the same user

    def _load_replied_users(self):
        """Loads the set of replied user IDs from the JSON file."""
        try:
            if os.path.exists(REPLIED_USERS_FILE):
                with open(REPLIED_USERS_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # Ensure all loaded IDs are strings for consistent comparison
                        return set(map(str, data))
                    else:
                        logger.warning(f"'{REPLIED_USERS_FILE}' contained invalid data type ({type(data)}), returning empty set for this load.")
                        return set()
            # logger.debug(f"'{REPLIED_USERS_FILE}' not found. Returning empty set.") # Can be noisy
            return set()
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from '{REPLIED_USERS_FILE}'. Returning empty set for this load.", exc_info=True)
            return set()
        except Exception:
            logger.error(f"Error loading replied users from '{REPLIED_USERS_FILE}'. Returning empty set for this load.", exc_info=True)
            return set()

    def _save_replied_users(self):
        """Saves the current set of replied user IDs to the JSON file."""
        try:
            with open(REPLIED_USERS_FILE, 'w') as f:
                # Convert set to list before saving to JSON
                json.dump(list(self.replied_users), f, indent=4)
        except Exception:
            logger.error(f"Error saving replied users to '{REPLIED_USERS_FILE}'.", exc_info=True)

    async def on_ready(self):
        if self.user is None:
             logger.error("Failed to log in, self.user is None. Check your token and library compatibility.")
             await self.close()
             return

        logger.info(f'Logged in as {self.user} ({self.user.id})')
        logger.warning("############################################################")
        logger.warning("### WARNING: RUNNING SELF-BOT! VIOLATES DISCORD ToS!     ###")
        logger.warning("### YOUR ACCOUNT IS AT RISK OF PERMANENT SUSPENSION!     ###")
        logger.warning("############################################################")
        # Start background tasks
        self.loop.create_task(self.post_periodically())
        # self.loop.create_task(self.check_dms_periodically()) # Optional: Periodic check as backup

    async def on_message(self, message):
        """Handle incoming messages, primarily for DMs."""
        # Ignore messages from self
        if message.author == self.user:
            return

        # Process only DMs
        # Use discord.DMChannel for type checking
        if isinstance(message.channel, discord.DMChannel):
            logger.debug(f"Received DM via on_message from {message.author} ({message.author.id})")
            await self.process_dm(message)
        # Optional: Add handling for other message types if needed
        # else:
        #     logger.debug(f"Ignoring non-DM message in {message.channel} from {message.author}")


    async def post_periodically(self):
        """Periodically posts a random message to the target channel."""
        await self.wait_until_ready()
        logger.info("Periodic message posting task started.")
        while not self.is_closed():
            try:
                # Use get_channel which should work fine
                channel = self.get_channel(TARGET_CHANNEL_ID)
                # Use discord.TextChannel for type checking
                if channel and isinstance(channel, discord.TextChannel):
                    chosen_message = random.choice(POST_MESSAGES)
                    await channel.send(chosen_message)
                    logger.info(f"Posted message in #{channel.name} ({channel.id})")
                elif channel:
                     logger.warning(f"Channel {TARGET_CHANNEL_ID} found, but it's not a TextChannel (Type: {type(channel)}). Cannot post.")
                else:
                    logger.warning(f"Target channel {TARGET_CHANNEL_ID} not found! Check the ID and bot's access.")

                sleep_time = random.randint(POST_INTERVAL_MIN_SECONDS, POST_INTERVAL_MAX_SECONDS)
                logger.info(f"Next post scheduled in {sleep_time / 60:.2f} minutes.")
                await asyncio.sleep(sleep_time)

            # Use standard discord exception types
            except discord.Forbidden:
                 logger.error(f"Permission error posting to channel {TARGET_CHANNEL_ID}. Check permissions.", exc_info=True)
                 await asyncio.sleep(300) # Wait longer if forbidden
            except discord.HTTPException as e:
                 logger.error(f"HTTP error posting message: {e.status} {getattr(e, 'text', 'No text')}", exc_info=True)
                 await asyncio.sleep(60)
            except Exception:
                logger.error("Unexpected error in posting task:", exc_info=True)
                await asyncio.sleep(60) # Wait a bit before retrying after other errors


    # --- Optional: Periodic DM Check ---
    async def check_dms_periodically(self):
        """Periodically checks recent DM history for unreplied messages."""
        await self.wait_until_ready()
        logger.info("Periodic DM check task started (backup mechanism).")
        while not self.is_closed():
            try:
                logger.debug("Running periodic DM check...")
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=MAX_DM_AGE_DAYS)

                # Iterate through cached private channels
                # Use self.private_channels which should be populated by the library
                for channel in self.private_channels:
                    # Use discord.DMChannel for type checking
                    if isinstance(channel, discord.DMChannel):
                        try:
                            # Fetch history. Permissions might still be an issue.
                            # Make sure 'after' is timezone-aware if comparing with aware message times
                            async for message in channel.history(limit=10, after=cutoff_time, oldest_first=False):
                                if message.author != self.user:
                                     user_id_str = str(message.author.id)
                                     # Before calling process_dm, reload replied users for this check as well if strictness is needed
                                     # current_replied_users_for_check = self._load_replied_users() # Optional: More I/O
                                     # if user_id_str not in current_replied_users_for_check:
                                     if user_id_str not in self.replied_users: # Uses the instance's current state (updated by on_message/process_dm)
                                          logger.info(f"[Periodic Check] Found potential missed DM from {message.author} ({user_id_str}). Processing.")
                                          await self.process_dm(message) # Pass the message object
                                     # else: # Optional debug log
                                     #     logger.debug(f"[Periodic Check] Skipping already replied user {message.author} ({user_id_str})")

                        except discord.Forbidden:
                             # Use getattr for recipient as it might not always be available depending on cache state
                             logger.warning(f"[Periodic Check] Cannot read history for DM with {getattr(channel, 'recipient', 'Unknown Recipient')} ({channel.id}) - Permission Error.")
                        except discord.HTTPException as e:
                             logger.warning(f"[Periodic Check] HTTP error reading history for DM with {getattr(channel, 'recipient', 'Unknown Recipient')} ({channel.id}): {e.status}")
                        except Exception:
                             logger.error(f"[Periodic Check] Unexpected error reading history for DM with {getattr(channel, 'recipient', 'Unknown Recipient')} ({channel.id}):", exc_info=True)

                logger.debug(f"Periodic DM check finished. Sleeping for {DM_CHECK_INTERVAL_SECONDS}s.")
                await asyncio.sleep(DM_CHECK_INTERVAL_SECONDS)

            except Exception:
                 logger.error("Unexpected error in periodic DM check task:", exc_info=True)
                 await asyncio.sleep(60) # Wait after error


    async def process_dm(self, message):
        """Handles the logic for potentially replying to a received DM."""
        author = message.author
        user_id_str = str(author.id) # Ensure comparison is always string vs string

        # === MODIFICATION: Reload replied users from file every time ===
        self.replied_users = self._load_replied_users()
        logger.debug(f"Refreshed replied users list from file for {author.id}. Count: {len(self.replied_users)}")
        # === END MODIFICATION ===

        # Check if message content is accessible (some forks might require specific flags/intents even for DMs)
        if not message.content and isinstance(message.channel, discord.DMChannel):
             logger.warning(f"Received DM from {author} ({user_id_str}) but message.content is empty. Processing based on reception, not content.")
             # Decide if you still want to process based purely on receiving *any* DM

        # Get or create lock for this user ID
        if user_id_str not in self.dm_handling_locks:
            self.dm_handling_locks[user_id_str] = asyncio.Lock()

        # Acquire lock for this user to prevent duplicate processing
        async with self.dm_handling_locks[user_id_str]:
            # Check if user already replied to *after* acquiring lock and *after* reloading the list
            if user_id_str in self.replied_users:
                logger.info(f"User {author} ({user_id_str}) is in the (refreshed) replied users list. Skipping DM.")
                return # Exit processing for this user

            # Check message age (ensure message.created_at is timezone-aware)
            # discord.py usually provides timezone-aware UTC datetimes
            now_utc = datetime.now(timezone.utc)
            message_age = now_utc - message.created_at
            if message_age > timedelta(days=MAX_DM_AGE_DAYS):
                logger.info(f"DM from {author} ({user_id_str}) is too old ({message_age}). Skipping.")
                return # Exit processing

            # Log message content if available, otherwise just note reception
            msg_preview = f"'{message.content[:50].replace(chr(10),' ')}...'" if message.content else "[Content Unavailable/Empty]"
            logger.info(f"User {author} ({user_id_str}) not found in (refreshed) replied users. Processing new DM. Message: {msg_preview}")

            # Introduce random delay before replying
            reply_delay = random.randint(DM_REPLY_DELAY_MIN_SECONDS, DM_REPLY_DELAY_MAX_SECONDS)
            logger.info(f"Waiting {reply_delay} seconds before replying to {author} ({user_id_str}).")
            await asyncio.sleep(reply_delay)

            try:
                # Send the DM reply
                await message.channel.send(DM_REPLY_MESSAGE)
                logger.info(f"Successfully sent DM reply to {author} ({user_id_str}).")

                # Add user to replied set (which was just reloaded) and save immediately
                self.replied_users.add(user_id_str)
                self._save_replied_users() # Save after successful reply and addition
                logger.info(f"Added {author} ({user_id_str}) to replied users list and saved. Total: {len(self.replied_users)}")

            # Use standard discord exceptions for error handling
            except discord.Forbidden:
                logger.error(f"Cannot send DM reply to {author} ({user_id_str}). Permissions error or user blocked DMs/Bot.", exc_info=False) # exc_info=False for brevity
            except discord.HTTPException as e:
                logger.error(f"HTTP error sending DM reply to {author} ({user_id_str}): {e.status} {getattr(e, 'text', 'No text')}", exc_info=False)
            except Exception:
                logger.error(f"Unexpected error sending DM reply to {author} ({user_id_str}):", exc_info=True) # Log full trace for unexpected


def main():
    client = SelfBotClient() 

    try:
        logger.info("Attempting to log in with token using discord.py-self...")
        logger.warning("--- SELF-BOT STARTING - ACCOUNT BAN RISK ---")
        client.run(TOKEN) # Standard way

    except discord.LoginFailure: # Standard exception
        logger.critical("LOGIN FAILED: Invalid token provided. Check the token.")
        print("\nEnsure you provided the correct user token as a command-line argument.")
        print("Example: python your_script_name.py YOUR_ACTUAL_TOKEN_HERE")
    # Catch potential exceptions during the run phase
    except discord.HTTPException as e:
         logger.critical(f"Discord HTTP error during connection/runtime: {e.status} {getattr(e, 'text', 'No text')}", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Shutdown initiated by user (Ctrl+C)...")
        # client.run() usually handles cleanup, but saving might need explicit handling
        # The save within process_dm is the most reliable during runtime
    except Exception as e:
        logger.critical(f"An unexpected error occurred during login or runtime: {e}", exc_info=True)
    finally:
        logger.warning("--- SELF-BOT SHUTTING DOWN ---")
        # This finally block might execute after client.run() finishes or errors out.
        # The save in process_dm is better for runtime state. This is a last resort.
        logger.info("Attempting final save of replied users (may not capture last operations if shutdown was abrupt).")
        # Check if client was successfully initialized and has the save method
        if 'client' in locals() and isinstance(client, SelfBotClient) and hasattr(client, '_save_replied_users'):
             client._save_replied_users()
             logger.info("Final save attempted.")
        else:
             logger.warning("Could not perform final save (client object invalid or missing method).")


if __name__ == "__main__":
    main()
    # Keep console open on Windows after script finishes/errors
    if os.name == 'nt':
        input("Press Enter to exit...")
