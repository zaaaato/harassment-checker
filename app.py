"""
Main application file for the Slack Moderation Bot.

This script initializes the Slack Bolt app, sets up message handlers,
and starts the Socket Mode handler to listen for Slack events.
It integrates with OpenAI for content moderation and sends notifications
based on the moderation results.
"""
import logging

# Import config module first. This is crucial as config.py initializes logging
# and loads all environment variables which are then available for other modules.
import config 

# Imports from Slack Bolt library for Slack integration.
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Imports from local application modules.
# These modules rely on configurations loaded by the 'config' import above.
from config import (
    # SLACK_BOT_TOKEN is used by create_slack_app internally via config.
    SLACK_APP_TOKEN,      # Required for SocketModeHandler.
    OPENAI_API_KEY,       # Checked here to ensure it was loaded, vital for moderation.
    HARASSMENT_CATEGORIES,# List of categories to check from OpenAI moderation.
    SLACK_NOTIFICATION_CHANNEL_ID # Optional channel for notifications.
)
from slack_integration import create_slack_app, register_message_handler
from openai_integration import moderate_text


# Get a logger instance for this module (app.py).
# Logging configuration (level, format) is already set by config.py.
logger = logging.getLogger(__name__)

# Initialize the Slack Bolt App instance using the function from slack_integration.
# This function internally uses SLACK_BOT_TOKEN from config.py.
# The 'app' object is central to handling Slack events and API calls.
app = create_slack_app() 

if not app:
    # This condition signifies a critical failure in initializing the Slack App,
    # likely due to SLACK_BOT_TOKEN not being configured (though config.py should catch this).
    # The application cannot proceed without a valid 'app' instance.
    logger.critical(
        "CRITICAL ERROR: Slack App (app object) could not be initialized. "
        "This often means SLACK_BOT_TOKEN is missing or invalid. Application cannot start."
    )
    # Consider exiting if in a production scenario: exit(1)
    # config.py already raises ValueError for missing essential keys, which should stop execution.


def message_moderation_handler(message: dict, say: callable):
    """
    Processes incoming Slack messages, moderates their text using OpenAI,
    and sends notifications if specific harassment categories are detected.

    This function is registered as a message handler with the Slack Bolt app.

    Args:
        message (dict): The Slack message event payload. This dictionary contains
                        details about the message, sender, channel, etc.
        say (callable): A utility function provided by Slack Bolt to send messages
                        back to the channel where the incoming message was received.
                        It can also be used to reply in a thread.
    
    Interactions:
    - Calls `openai_integration.moderate_text` to get moderation analysis.
    - Checks the result against `HARASSMENT_CATEGORIES` from `config.py`.
    - Sends notifications using `say` (for threaded replies or same-channel messages)
      or `app.client.chat_postMessage` (for a dedicated notification channel,
      if `SLACK_NOTIFICATION_CHANNEL_ID` is configured).
    """
    # Extract the text content and user ID from the message payload.
    # Provide defaults for logging in case these fields are unexpectedly missing.
    text_to_moderate = message.get('text')
    user_id = message.get('user', 'UnknownUser') 
    message_id = message.get('client_msg_id', 'UnknownMsgId') # Unique ID for the message, useful for logging.
    channel_id = message.get('channel', 'UnknownChannel')     # ID of the channel where the message was posted.
    message_ts = message.get('ts')                            # Timestamp of the message, used for threading replies.

    # If there's no text in the message (e.g., an attachment-only message, or certain event types), skip processing.
    if not text_to_moderate:
        logger.debug(
            f"Skipping message (ID: {message_id}) from user {user_id} in channel {channel_id} "
            "as it contains no text to moderate."
        )
        return

    logger.info(
        f"Moderating message (ID: {message_id}) from user <@{user_id}> in channel <#{channel_id}>. "
        f"Text: \"{text_to_moderate[:100]}...\"" # Log a snippet of the message.
    )

    # Call the OpenAI moderation API via the wrapper function in openai_integration.
    moderation_result = moderate_text(text_to_moderate)

    # If the moderation call fails (e.g., API error, network issue), moderate_text returns None.
    if moderation_result is None:
        logger.error(
            f"OpenAI Moderation API call failed for message ID {message_id} "
            f"from user <@{user_id}> in channel <#{channel_id}>. "
            f"Original text: \"{text_to_moderate[:100]}...\""
        )
        # Optionally, you could inform the user or channel about the error, but be cautious.
        # e.g., say(text=f"Sorry <@{user_id}>, I couldn't process your message due to a moderation system error.")
        return

    # Collect categories that were flagged as True by OpenAI and are in our HARASSMENT_CATEGORIES list.
    detected_categories = []
    # The OpenAI SDK's moderation result object has a 'categories' attribute,
    # which itself has boolean attributes for each category (e.g., categories.harassment).
    # HARASSMENT_CATEGORIES in config.py stores these as underscore_separated strings.
    for category_name in HARASSMENT_CATEGORIES: 
        # Use getattr to safely access the category attribute on the moderation_result.categories object.
        # Defaults to False if the category_name attribute doesn't exist for some reason.
        if getattr(moderation_result.categories, category_name, False):
            # Convert underscore_style back to slash/style for display if desired, or keep as is.
            detected_categories.append(category_name.replace('_', '/')) 

    # If any of our specified harassment categories were detected:
    if detected_categories:
        display_categories = ', '.join(detected_categories) # Format for the notification message.
        
        # Construct a direct Slack link to the original message.
        original_message_link = "original message (link unavailable)"
        if channel_id != 'UnknownChannel' and message_ts:
            original_message_link = f"slack://channel/{channel_id}/p{message_ts.replace('.', '')}"

        # Prepare the notification text.
        notification_text = (
            f":warning: Message from <@{user_id}> in <#{channel_id}> flagged for: *{display_categories}*.\n"
            f"> Original message: <{original_message_link}>\n" # Link to the original message.
            f"> _{text_to_moderate}_" # Quote the original message text.
        )
        
        logger.info(
            f"Message (ID: {message_id}) from <@{user_id}> in <#{channel_id}> flagged for: {display_categories}. "
            "Sending notification."
        )
        try:
            # If a specific notification channel is configured, send the message there.
            if SLACK_NOTIFICATION_CHANNEL_ID:
                logger.info(
                    f"Sending notification for message ID {message_id} to dedicated channel: {SLACK_NOTIFICATION_CHANNEL_ID}"
                )
                # Use app.client.chat_postMessage for sending to a specific channel.
                # This requires the 'chat:write' bot scope.
                app.client.chat_postMessage(
                    channel=SLACK_NOTIFICATION_CHANNEL_ID,
                    text=notification_text
                )
            else:
                # If no dedicated channel, reply in a thread to the original message (or just in channel if no ts).
                reply_target_log = f"channel {channel_id}"
                if message_ts:
                    reply_target_log = f"thread {message_ts} in channel {channel_id}"

                logger.info(
                    f"Replying in {reply_target_log} for message ID {message_id}."
                )
                if not message_ts: 
                     logger.warning(
                         f"Message (ID: {message_id}) from user {user_id} is missing 'ts' (timestamp). "
                         "Cannot reply in thread. Sending notification directly to channel."
                     )
                     say(text=notification_text) # Send to channel if no 'ts' (e.g. for some event types)
                else:
                     say(text=notification_text, thread_ts=message_ts) # Reply in thread.
            logger.info(f"Successfully sent moderation notification for user <@{user_id}> (message ID: {message_id}).")
        except Exception as e:
            logger.exception(
                f"Error sending Slack notification for message ID {message_id} "
                f"from user <@{user_id}>: {e}"
            )
    else:
        # Log if the message was flagged by OpenAI overall but not for any of our specified categories.
        # This helps in understanding if HARASSMENT_CATEGORIES list needs adjustment.
        openai_flag_status_log = "flagged by OpenAI" if moderation_result.flagged else "clean"
        if moderation_result.flagged:
            all_openai_flagged_categories = [
                cat.replace('_', '/') for cat, val in moderation_result.categories.__dict__.items() if val
            ]
            details = (
                f"(OpenAI overall_flagged: {moderation_result.flagged}. "
                f"OpenAI Categories: {all_openai_flagged_categories if all_openai_flagged_categories else 'None specific'})"
            )
        else:
            details = f"(OpenAI overall_flagged: {moderation_result.flagged})"
            
        logger.info(
            f"Message (ID: {message_id}) from <@{user_id}> in <#{channel_id}> determined {openai_flag_status_log} "
            f"and not matching local HARASSMENT_CATEGORIES. {details} "
            f"Text: \"{text_to_moderate[:50]}...\""
        )


# Register the message_moderation_handler with the Slack app instance.
# This tells the app to call this function whenever a new message event is received.
if app:
    register_message_handler(app, message_moderation_handler)
else:
    # This case should ideally be prevented by earlier checks or errors in config.py/create_slack_app.
    logger.critical(
        "CRITICAL ERROR: Slack app object is None. Cannot register message handler. Application will not process messages."
    )

# This block executes only if the script is run directly (e.g., `python app.py`).
if __name__ == "__main__":
    logger.info("Starting Slack Moderation Bot application...")
    
    # Perform final checks before starting.
    # Essential API keys (SLACK_BOT_TOKEN, OPENAI_API_KEY) are validated in config.py.
    # SLACK_APP_TOKEN is also validated in config.py as it's essential for SocketModeHandler.
    if not app:
        # This is a final safeguard. If 'app' is None here, it means create_slack_app() failed.
        logger.critical(
            "Application cannot start: Slack app instance ('app') is not initialized. "
            "Check previous logs for errors, especially regarding SLACK_BOT_TOKEN."
        )
    # SLACK_APP_TOKEN is specifically required by SocketModeHandler.
    # config.py should have already raised an error if it's missing.
    elif not SLACK_APP_TOKEN: 
        logger.critical(
            "Application cannot start: SLACK_APP_TOKEN is not configured. "
            "SocketModeHandler requires it. Check .env file or environment variables."
        )
    else:
        logger.info("Slack Bot Token, App Token, and OpenAI API Key are configured.")
        logger.info("Attempting to start Slack SocketModeHandler...")
        try:
            # Start the Socket Mode handler. This connects to Slack and begins listening for events.
            # It's a blocking call, so it will keep the application running.
            SocketModeHandler(app, SLACK_APP_TOKEN).start()
        except Exception as e:
            # Log critical errors that prevent the SocketModeHandler from starting.
            logger.critical(f"FATAL: Failed to start SocketModeHandler: {e}", exc_info=True)
            logger.critical(
                "Ensure SLACK_APP_TOKEN is correct and the Slack App is configured for Socket Mode in its settings. "
                "Also check network connectivity."
            )
