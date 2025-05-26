import discord # Use the standard import name
import sys
import os
import random
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone # Use timezone-aware datetimes

# --- Configuration ---
# <<< NEW: Global flag for disabling staggering, set by command-line arg >>>
DISABLE_STAGGERING = False

# <<< NEW: Configuration for initial post staggering >>>
# This is the delay *between* each bot's first post.
# If bot 0 posts at T, bot 1 will post at T + INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS, etc.
INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS = 30 * 60 # 30 minutes (e.g., 1800 seconds)
# Small base delay for the very first bot (index 0) or as a base for all,
# to ensure it's fully ready or just to add a small buffer.
MIN_INITIAL_POST_DELAY_SECONDS = 0 # No additional delay for the first bot by default

# <<< MODIFIED: Command line argument parsing >>>
if not (3 <= len(sys.argv) <= 4): # Expecting script_name, token, instance_index, and optional -r
    print("Usage: python discord_selfbot_script.py <your_user_token> <instance_index> [-r]")
    print("WARNING: Using your user token for automation violates Discord ToS.")
    print("<instance_index> should be a 0-based integer assigned by the launcher.")
    print("  -r : Optional. If present, disables initial post staggering for this instance.")
    sys.exit(1)

TOKEN = sys.argv[1] # This will be YOUR_USER_TOKEN passed by bots.py
try:
    INSTANCE_INDEX = int(sys.argv[2])
    if INSTANCE_INDEX < 0:
        raise ValueError("Instance index must be non-negative.")
except ValueError as e:
    print(f"Error: Invalid instance_index '{sys.argv[2]}'. It must be a non-negative integer. {e}")
    sys.exit(1)

if len(sys.argv) == 4:
    if sys.argv[3] == "-r":
        DISABLE_STAGGERING = True
    else:
        print(f"Error: Unknown optional argument '{sys.argv[3]}'. Expected '-r' or no optional argument.")
        print("Usage: python discord_selfbot_script.py <your_user_token> <instance_index> [-r]")
        sys.exit(1)


# --- CORE CONFIGURATION TO BE MODIFIED BY USER ---
TARGET_CHANNEL_ID = YOUR_TARGET_CHANNEL_ID_HERE # Example: 123456789012345678 (Integer or String)
# <<< MODIFIED: Shared replied users file for ALL instances >>>
REPLIED_USERS_FILE = "replied_users.json" # File to store IDs of users already replied to (usually keep as is)

# Posting intervals (can be adjusted as needed)
POST_INTERVAL_MIN_SECONDS = 2 * 60 * 60 # Minimum time between posts (e.g., 2 hours = 7200 seconds)
POST_INTERVAL_MAX_SECONDS = 2 * 60 * 60 # Maximum time between posts (e.g., 2 hours = 7200 seconds)

# DM handling settings
DM_REPLY_DELAY_MIN_SECONDS = 50   # Min seconds before replying to a DM
DM_REPLY_DELAY_MAX_SECONDS = 200  # Max seconds before replying to a DM
DM_CHECK_INTERVAL_SECONDS = 60 * 5 # How often to periodically check DMs (e.g., 5 minutes). NOTE: This check is DISABLED by default below.
MAX_DM_AGE_DAYS = 1             # Only reply to DMs newer than this
DM_REPLY_MESSAGE = "YOUR_CUSTOM_DM_REPLY_MESSAGE_HERE" # Message to send in reply (e.g., "Thanks for your message! Check out discord.gg/yourserver")

# --- Messages to Post ---
# Replace these with your desired messages.
POST_MESSAGES = [
    """
    **YOUR_AD_MESSAGE_1_TITLE**
    - Detail 1: Value 1
    - Detail 2: Value 2
    - Call to Action: Message me or join our Discord!
    """,
    """
    **YOUR_AD_MESSAGE_2_TITLE**
    > Some other format you might like.
    > - Point A
    > - Point B
    > More info in DMs!
    """,
    # Add more messages as needed, following Python string conventions (triple quotes for multi-line).
]
# --- END OF CORE CONFIGURATION ---


# --- Logging Setup ---
LOG_FILE_NAME = f"selfbot_instance_{INSTANCE_INDEX}.log" # <<< MODIFIED: Unique log file per instance >>>

log_formatter = logging.Formatter(f'%(asctime)s [Bot-{INSTANCE_INDEX}] [%(levelname)s] %(message)s')

# Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# File Handler
file_handler = None # Initialize to None
try:
    file_handler = logging.FileHandler(LOG_FILE_NAME, mode='a', encoding='utf-8') # Append mode, utf-8 encoding
    file_handler.setFormatter(log_formatter)
except Exception as e:
    print(f"CRITICAL [Bot-{INSTANCE_INDEX}]: Could not set up log file '{LOG_FILE_NAME}'. Error: {e}", file=sys.stderr)

logger = logging.getLogger(f'discord_selfbot_inst{INSTANCE_INDEX}') # Unique logger name per instance
logger.setLevel(logging.INFO)

if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    logger.addHandler(console_handler)
if file_handler and not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    logger.addHandler(file_handler)


# --- Self-Bot Class ---
class SelfBotClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)
        logger.info("Bot initializing using discord.py-self (no explicit intents)...")
        self.replied_users = self._load_replied_users()
        logger.info(f"Initially loaded {len(self.replied_users)} replied user IDs from SHARED file '{REPLIED_USERS_FILE}'")
        self.dm_handling_locks = {}

    def _load_replied_users(self):
        try:
            for _ in range(3): # Retry logic
                try:
                    if os.path.exists(REPLIED_USERS_FILE):
                        with open(REPLIED_USERS_FILE, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            return set(map(str, data)) if isinstance(data, list) else set()
                    return set()
                except (IOError, json.JSONDecodeError) as e:
                    logger.warning(f"Retrying _load_replied_users due to: {e}")
                    asyncio.sleep(random.uniform(0.1, 0.5)) # type: ignore
            logger.error(f"Failed to load replied users from '{REPLIED_USERS_FILE}' after retries.", exc_info=True)
            return set()
        except Exception:
            logger.error(f"Unexpected error loading replied users from '{REPLIED_USERS_FILE}'.", exc_info=True)
            return set()

    def _save_replied_users(self):
        try:
            for _ in range(3): # Retry logic
                try:
                    with open(REPLIED_USERS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(list(map(str, self.replied_users)), f, indent=4)
                    return
                except IOError as e:
                    logger.warning(f"Retrying _save_replied_users due to: {e}")
                    asyncio.sleep(random.uniform(0.1, 0.5)) # type: ignore
            logger.error(f"Failed to save replied users to '{REPLIED_USERS_FILE}' after retries.", exc_info=True)
        except Exception:
            logger.error(f"Unexpected error saving replied users to '{REPLIED_USERS_FILE}'.", exc_info=True)

    async def on_ready(self):
        if self.user is None:
             logger.error("Failed to log in, self.user is None. Check token and library.")
             await self.close()
             return

        logger.info(f'Logged in as {self.user} ({self.user.id})')
        logger.warning("############################################################")
        logger.warning("### WARNING: RUNNING SELF-BOT! VIOLATES DISCORD ToS!     ###")
        logger.warning("### YOUR ACCOUNT IS AT RISK OF PERMANENT SUSPENSION!     ###")
        logger.warning("### Auto-blocking users is also a risky automation.      ###")
        logger.warning("############################################################")

        # <<< MODIFICATION: Periodic DM Check is now DISABLED by default >>>
        # To re-enable, uncomment the line below.
        # self.loop.create_task(self.check_dms_periodically())
        logger.info("Periodic DM checking task is DISABLED. DMs will only be processed via on_message event.")
        
        self.loop.create_task(self.post_periodically())

    async def on_message(self, message):
        if message.author == self.user:
            return
        if isinstance(message.channel, discord.DMChannel):
            logger.debug(f"Received DM via on_message from {message.author} ({message.author.id})")
            await self.process_dm(message)

    async def post_periodically(self):
        await self.wait_until_ready()
        
        initial_sleep_duration: int
        if DISABLE_STAGGERING:
            initial_sleep_duration = MIN_INITIAL_POST_DELAY_SECONDS
            delay_reason = "staggering DISABLED by -r flag"
            if initial_sleep_duration > 0:
                logger.info(f"Instance {INSTANCE_INDEX}: Initial {delay_reason}. Effective base delay: {initial_sleep_duration // 60}m {initial_sleep_duration % 60}s.")
            else:
                logger.info(f"Instance {INSTANCE_INDEX}: Initial {delay_reason}. No initial delay.")
        else:
            stagger_component = INSTANCE_INDEX * INITIAL_POST_STAGGER_PER_INSTANCE_SECONDS
            initial_sleep_duration = MIN_INITIAL_POST_DELAY_SECONDS + stagger_component
            delay_reason = "staggering ENABLED"
            if stagger_component > 0:
                logger.info(f"Instance {INSTANCE_INDEX}: Initial {delay_reason}. Total delay (base + stagger): {initial_sleep_duration // 60}m {initial_sleep_duration % 60}s.")
            elif initial_sleep_duration > 0:
                 logger.info(f"Instance {INSTANCE_INDEX}: Initial {delay_reason} (Instance {INSTANCE_INDEX}, using base delay): {initial_sleep_duration // 60}m {initial_sleep_duration % 60}s.")
            else:
                 logger.info(f"Instance {INSTANCE_INDEX}: Initial {delay_reason}. No initial post delay or base delay.")
        
        if initial_sleep_duration > 0:
            logger.info(f"Sleeping for {initial_sleep_duration // 60}m {initial_sleep_duration % 60}s before first post.")
            await asyncio.sleep(initial_sleep_duration)
        else:
            logger.info(f"Instance {INSTANCE_INDEX}: Initial delay is 0. Posting soon.")

        logger.info("Periodic message posting task started (after initial delay/stagger if any).")
        while not self.is_closed():
            try:
                if not POST_MESSAGES:
                    logger.warning("POST_MESSAGES list is empty. No messages to post. Sleeping for interval.")
                else:
                    channel = self.get_channel(TARGET_CHANNEL_ID)
                    if channel and isinstance(channel, discord.TextChannel):
                        chosen_message = random.choice(POST_MESSAGES)
                        await channel.send(chosen_message)
                        logger.info(f"Posted message in #{channel.name} ({channel.id})")
                    elif channel:
                        logger.warning(f"Channel {TARGET_CHANNEL_ID} found, but it's not a TextChannel (Type: {type(channel)}). Cannot post.")
                    else:
                        logger.warning(f"Target channel {TARGET_CHANNEL_ID} not found! Check ID and bot's access.")

                sleep_time = random.randint(POST_INTERVAL_MIN_SECONDS, POST_INTERVAL_MAX_SECONDS)
                logger.info(f"Next post scheduled in {sleep_time / 60:.2f} minutes (approx. {sleep_time // 3600}h {(sleep_time % 3600) // 60}m).")
                await asyncio.sleep(sleep_time)
            except discord.Forbidden:
                 logger.error(f"Permission error posting to channel {TARGET_CHANNEL_ID}. Check permissions.", exc_info=True)
                 await asyncio.sleep(300)
            except discord.HTTPException as e:
                 logger.error(f"HTTP error posting message: {e.status} {getattr(e, 'text', 'No text')}", exc_info=True)
                 await asyncio.sleep(60)
            except Exception:
                logger.error("Unexpected error in posting task:", exc_info=True)
                await asyncio.sleep(60)

    # <<< MODIFICATION: This entire function is kept for completeness, but the task that calls it is disabled in on_ready() >>>
    # <<< To re-enable, uncomment its task creation in on_ready() >>>
    async def check_dms_periodically(self):
        logger.info("Periodic DM check task invoked. NOTE: This task is usually disabled by default.")
        await self.wait_until_ready()
        logger.info("Periodic DM check task started (backup mechanism, currently likely inactive).")
        while not self.is_closed():
            try:
                logger.debug("Running periodic DM check...")
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=MAX_DM_AGE_DAYS)
                current_private_channels = list(self.private_channels) # Make a copy
                logger.debug(f"Checking {len(current_private_channels)} cached private channels.")

                for channel_idx, channel in enumerate(current_private_channels): 
                    if isinstance(channel, discord.DMChannel):
                        recipient_name = getattr(channel.recipient, 'name', f'Unknown Recipient ID {getattr(channel.recipient, "id", "N/A")}')
                        try:
                            if channel_idx > 0 and channel_idx % 10 == 0 : await asyncio.sleep(0.5)
                            # Iterate in reverse (newest first) but only up to a limit or after cutoff
                            async for message in channel.history(limit=10, after=cutoff_time, oldest_first=False):
                                if message.author != self.user:
                                     user_id_str = str(message.author.id)
                                     # Crucial: Reload replied users for most up-to-date check
                                     current_replied_users_snapshot = self._load_replied_users()
                                     if user_id_str not in current_replied_users_snapshot:
                                          logger.info(f"[Periodic Check] Found potential unreplied DM from {message.author} ({user_id_str}) in DM with {recipient_name}. Processing.")
                                          await self.process_dm(message)
                                     else:
                                          logger.debug(f"[Periodic Check] DM from {message.author} ({user_id_str}) already in (SHARED, freshly loaded) replied list. Skipping.")
                                     break # Only process the newest unreplied message per DM channel per check
                        except discord.Forbidden:
                             logger.warning(f"[Periodic Check] Cannot read history for DM with {recipient_name} ({channel.id}) - Permission Error.")
                        except discord.HTTPException as e:
                             logger.warning(f"[Periodic Check] HTTP error reading history for DM with {recipient_name} ({channel.id}): {e.status}")
                        except Exception:
                             logger.error(f"[Periodic Check] Unexpected error reading history for DM with {recipient_name} ({channel.id}):", exc_info=True)
                logger.debug(f"Periodic DM check finished. Sleeping for {DM_CHECK_INTERVAL_SECONDS}s.")
                await asyncio.sleep(DM_CHECK_INTERVAL_SECONDS)
            except Exception:
                 logger.error("Unexpected error in periodic DM check task outer loop:", exc_info=True)
                 await asyncio.sleep(DM_CHECK_INTERVAL_SECONDS / 2 if DM_CHECK_INTERVAL_SECONDS > 20 else 10)

    async def on_resumed(self):
        logger.info("EVENT: Gateway session has been RESUMED successfully.")
        logger.debug(f"DEBUG: Number of private_channels after resume: {len(self.private_channels)}")

    async def process_dm(self, message: discord.Message):
        author = message.author
        if not isinstance(author, discord.User):
            logger.warning(f"DM author is not a discord.User object (Type: {type(author)}). Cannot process DM for blocking. Author: {author}")
            return
            
        user_id_str = str(author.id)

        if user_id_str not in self.dm_handling_locks:
            self.dm_handling_locks[user_id_str] = asyncio.Lock()

        async with self.dm_handling_locks[user_id_str]:
            # Always load fresh replied users list at the beginning of processing for a user
            self.replied_users = self._load_replied_users()
            logger.debug(f"process_dm: Refreshed replied users from SHARED file for {author.id} (inside lock). Count: {len(self.replied_users)}")

            if user_id_str in self.replied_users:
                logger.info(f"User {author} ({user_id_str}) is ALREADY in (refreshed SHARED) replied users list. Skipping DM processing.")
                return

            now_utc = datetime.now(timezone.utc)
            if message.created_at.tzinfo is None:
                message_created_at_utc = message.created_at.replace(tzinfo=timezone.utc)
            else:
                message_created_at_utc = message.created_at.astimezone(timezone.utc)

            message_age = now_utc - message_created_at_utc
            if message_age > timedelta(days=MAX_DM_AGE_DAYS):
                logger.info(f"DM from {author} ({user_id_str}) is too old ({message_age.days}d {message_age.seconds//3600}h). Skipping.")
                return

            msg_preview = f"'{message.content[:50].replace(chr(10),' ')}...'" if message.content else "[Content Unavailable/Empty]"
            logger.info(f"User {author} ({user_id_str}) NOT in SHARED replied users. Processing new DM. Message: {msg_preview}")

            reply_delay = random.randint(DM_REPLY_DELAY_MIN_SECONDS, DM_REPLY_DELAY_MAX_SECONDS)
            logger.info(f"Waiting {reply_delay} seconds before replying to {author} ({user_id_str}).")
            await asyncio.sleep(reply_delay)

            sent_successfully = False
            max_send_retries = 2
            send_retry_delay_base = 5

            for attempt in range(max_send_retries + 1):
                try:
                    await message.channel.send(DM_REPLY_MESSAGE)
                    logger.info(f"Successfully sent DM reply to {author} ({user_id_str}).")
                    sent_successfully = True
                    break
                except discord.Forbidden:
                    logger.error(f"CANNOT SEND DM (FORBIDDEN) to {author} ({user_id_str}). No retry.", exc_info=False)
                    break # Cannot send, no point retrying
                except discord.HTTPException as e:
                    if 500 <= e.status < 600: # Server-side errors, retryable
                        if attempt < max_send_retries:
                            retry_after_seconds = send_retry_delay_base * (2 ** attempt)
                            logger.warning(f"HTTP error {e.status} sending DM to {author} ({user_id_str}). Retrying ({attempt+1}/{max_send_retries}) in {retry_after_seconds}s.", exc_info=False)
                            await asyncio.sleep(retry_after_seconds)
                        else:
                            logger.error(f"HTTP error {e.status} sending DM to {author} ({user_id_str}) after {max_send_retries} retries.", exc_info=False)
                    elif e.status == 429: # Rate limited
                        retry_after_header_val = e.response.headers.get('Retry-After') if hasattr(e, 'response') and e.response else getattr(e, 'retry_after', None)
                        wait_time = float(retry_after_header_val) if retry_after_header_val else (send_retry_delay_base * (2 ** attempt))
                        log_msg = f"CANNOT SEND DM (RATE LIMITED {e.status}) to {author} ({user_id_str})."
                        log_msg += f" Discord suggests waiting {wait_time:.2f}s."
                        logger.error(log_msg + " No retry for THIS message.", exc_info=False)
                        break # Rate limited, stop trying for this message
                    else: # Other HTTP errors (e.g., 400, 403 handled by Forbidden, 404)
                        logger.error(f"HTTP error {e.status} sending DM to {author} ({user_id_str}). No retry.", exc_info=False)
                        break
                except Exception:
                    logger.error(f"Unexpected error sending DM reply to {author} ({user_id_str}). Attempt {attempt+1}.", exc_info=True)
                    if attempt < max_send_retries:
                         await asyncio.sleep(send_retry_delay_base * (2 ** attempt))
                
                if attempt == max_send_retries and not sent_successfully: # Should only be reached if retries exhausted for 5xx errors
                    logger.error(f"Failed to send DM to {author} ({user_id_str}) after all retries.", exc_info=False)

            if sent_successfully:
                self.replied_users.add(user_id_str) # Add to in-memory set
                self._save_replied_users()         # Save the updated set to file
                logger.info(f"Added {author} ({user_id_str}) to replied users list and saved to SHARED file. Total in memory: {len(self.replied_users)}")

                # <<< NEW: Block user after replying >>>
                try:
                    logger.info(f"Attempting to block user {author} ({user_id_str})...")
                    await author.block() # message.author is a discord.User object
                    logger.info(f"Successfully blocked user {author} ({user_id_str}).")
                except discord.Forbidden:
                    logger.error(f"Failed to block user {author} ({user_id_str}) - Forbidden. This account may not have permission or the user cannot be blocked.", exc_info=False)
                except discord.HTTPException as e_block:
                    logger.error(f"Failed to block user {author} ({user_id_str}) - HTTP Exception {e_block.status}.", exc_info=False)
                except Exception as e_block_unexpected:
                    logger.error(f"Unexpected error blocking user {author} ({user_id_str}).", exc_info=True)
                # <<< END NEW >>>
            else:
                logger.warning(f"Ultimately FAILED to send DM reply to {author} ({user_id_str}). User not added to replied list. Will not attempt to block.")
        
        # Clean up lock if it's no longer needed and not locked
        if user_id_str in self.dm_handling_locks and not self.dm_handling_locks[user_id_str].locked():
             try:
                 del self.dm_handling_locks[user_id_str]
                 logger.debug(f"Cleaned up DM handling lock for user {user_id_str}")
             except KeyError:
                 pass # Already deleted, race condition, fine.


# --- Main Execution ---
def main_selfbot():
    client = SelfBotClient() # For discord.py-self

    try:
        logger.info(f"Attempting to log in with token for instance {INSTANCE_INDEX} using discord.py-self...")
        if DISABLE_STAGGERING:
            logger.info("Initial post staggering is DISABLED for this instance via -r flag.")
        else:
            logger.info("Initial post staggering is ENABLED for this instance.")
        logger.info(f"Logs for this instance are also being saved to: {LOG_FILE_NAME}")
        
        # Ensure TARGET_CHANNEL_ID is an integer if it's a string
        global TARGET_CHANNEL_ID
        try:
            TARGET_CHANNEL_ID = int(TARGET_CHANNEL_ID)
        except ValueError:
            logger.critical(f"Configuration Error: TARGET_CHANNEL_ID ('{TARGET_CHANNEL_ID}') is not a valid integer. Please set it correctly.")
            sys.exit(1)
        if TARGET_CHANNEL_ID == YOUR_TARGET_CHANNEL_ID_HERE: # Check if placeholder is still there
             logger.critical("Configuration Error: TARGET_CHANNEL_ID is still set to the placeholder 'YOUR_TARGET_CHANNEL_ID_HERE'. Please update it in the script.")
             sys.exit(1)
        if DM_REPLY_MESSAGE == "YOUR_CUSTOM_DM_REPLY_MESSAGE_HERE":
            logger.warning("Configuration Warning: DM_REPLY_MESSAGE is still set to the placeholder. It will send this placeholder text if a DM is replied to.")
        if not POST_MESSAGES or (len(POST_MESSAGES) == 1 and "YOUR_AD_MESSAGE" in POST_MESSAGES[0]):
            logger.warning("Configuration Warning: POST_MESSAGES list seems to contain only placeholders or is empty. The bot might not post anything or post placeholder text.")


        logger.warning("--- SELF-BOT STARTING - ACCOUNT BAN RISK ---")
        client.run(TOKEN) # TOKEN is passed as sys.argv[1]
    except discord.LoginFailure:
        logger.critical("LOGIN FAILED: Invalid token provided. Check the token.")
    except discord.HTTPException as e:
         logger.critical(f"Discord HTTP error during connection/runtime: {e.status} {getattr(e, 'text', 'No text')}", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Shutdown initiated by user (Ctrl+C)...")
    except Exception:
        logger.critical(f"An UNEXPECTED CRITICAL error occurred in main_selfbot for instance {INSTANCE_INDEX}:", exc_info=True)
    finally:
        logger.warning("--- SELF-BOT SHUTTING DOWN ---")
        if 'client' in locals() and isinstance(client, SelfBotClient) and hasattr(client, '_save_replied_users'):
             if not client.is_closed(): # type: ignore
                 logger.info("Client connection may not be closed. Attempting final save.")
             client._save_replied_users() 
             logger.info(f"Final save of replied users to SHARED file '{REPLIED_USERS_FILE}' attempted.")
        else:
             logger.warning("Could not perform final save (client object invalid or not fully initialized).")

if __name__ == "__main__":
    # Basic check for placeholder in token (though token comes from argv)
    if TOKEN == "YOUR_USER_TOKEN_PLACEHOLDER": # Generic placeholder check
        print("CRITICAL ERROR: The token provided appears to be a placeholder. Please use a real Discord user token.", file=sys.stderr)
        sys.exit(1)
        
    try:
        main_selfbot()
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        inst_idx_str = str(INSTANCE_INDEX) if 'INSTANCE_INDEX' in globals() else "UNKNOWN"
        error_message = f"{timestamp} [Bot-{inst_idx_str}] [CRITICAL] Top-level unhandled exception in __main__: {e}\n"
        log_file_to_use = LOG_FILE_NAME if 'LOG_FILE_NAME' in globals() else f"selfbot_instance_{inst_idx_str}_error.log"
        try:
            with open(log_file_to_use, 'a', encoding='utf-8') as f_err:
                import traceback
                f_err.write(error_message)
                traceback.print_exc(file=f_err)
        except: 
            pass # Cannot log to file, print to stderr
        print(error_message, file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
    finally:
        inst_idx_str = str(INSTANCE_INDEX) if 'INSTANCE_INDEX' in globals() else "UNKNOWN"
        final_msg = f"Instance {inst_idx_str} processing finished and script is exiting."
        if logger and logger.handlers: # Check if logger was initialized
             logger.info(final_msg)
        else:
             print(final_msg + " (logger not fully available).", file=sys.stderr)
