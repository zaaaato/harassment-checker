import logging # Import logging

# Import config first to ensure logging is configured early
import config 
from slack_bolt.adapter.socket_mode import SocketModeHandler
# Then, imports from local modules (config is already imported)
from config import (
    SLACK_BOT_TOKEN, # Though create_slack_app uses it from config directly
    SLACK_APP_TOKEN,
    OPENAI_API_KEY,  # For the main block check, ensuring it was loaded
    HARASSMENT_CATEGORIES,
    SLACK_NOTIFICATION_CHANNEL_ID
)
from slack_integration import create_slack_app, register_message_handler
from openai_integration import moderate_text


logger = logging.getLogger(__name__) # Get a logger instance

# Initialize the Slack app using settings from config.py
# create_slack_app now takes no arguments as it uses config internally
app = create_slack_app() # This will log success or critical failure from slack_integration

if not app:
    # This log is a bit redundant if create_slack_app logs the critical error,
    # but it confirms at the app level that initialization failed.
    logger.critical("CRITICAL ERROR: Slack App could not be initialized. Application cannot proceed.")
    # Depending on desired behavior, might exit or raise an error
    # exit(1) # config.py will raise ValueError if essential keys are missing, stopping execution.

def message_moderation_handler(message, say):
    """
    Handles incoming messages, calls OpenAI for moderation, and sends a notification
    if harassment-related categories are detected.
    Notifications are sent to SLACK_NOTIFICATION_CHANNEL_ID if set, otherwise replied in thread/channel.
    """
    text_to_moderate = message.get('text')
    user_id = message.get('user', 'UnknownUser') # Default if not present
    message_id = message.get('client_msg_id', 'UnknownMsgId')  # For logging
    channel_id = message.get('channel', 'UnknownChannel') # For logging and linking
    message_ts = message.get('ts') # For threading or linking

    if not text_to_moderate:
        logger.debug(f"Skipping empty or non-text message from user {user_id} in channel {channel_id} (msg_id: {message_id}).")
        return

    logger.info(f"Moderating message from <@{user_id}> in channel <#{channel_id}> (msg_id: {message_id}): \"{text_to_moderate[:100]}...\"")

    moderation_result = moderate_text(text_to_moderate)

    if moderation_result is None:
        logger.error(f"Moderation API call failed for message ID {message_id} from user <@{user_id}> in channel <#{channel_id}>. Original text: \"{text_to_moderate[:100]}...\"")
        # Consider whether to notify user/channel about the error
        # try:
        #     say(f"Sorry <@{user_id}>, I couldn't process your message due to a moderation system error.")
        # except Exception as e:
        #     logger.error(f"Failed to send error message to Slack: {e}")
        return

    detected_categories = []
    for category_name in HARASSMENT_CATEGORIES: # Use HARASSMENT_CATEGORIES from config
        if getattr(moderation_result.categories, category_name, False):
            detected_categories.append(category_name.replace('_', '/')) 

    if detected_categories:
        display_categories = ', '.join(detected_categories)
        
        original_message_link = f"slack://channel/{channel_id}/p{message_ts.replace('.', '')}" if channel_id != 'UnknownChannel' and message_ts else "original message (link unavailable)"

        notification_text = (
            f":warning: Message from <@{user_id}> in <#{channel_id}> flagged for: *{display_categories}*.\n"
            f"> Original message: <{original_message_link}>\n"
            f"> _{text_to_moderate}_"
        )
        
        logger.info(f"Message from <@{user_id}> in <#{channel_id}> (msg_id: {message_id}) flagged for: {display_categories}. Notifying.")
        try:
            if SLACK_NOTIFICATION_CHANNEL_ID:
                logger.info(f"Sending notification for msg_id {message_id} to dedicated channel: {SLACK_NOTIFICATION_CHANNEL_ID}")
                app.client.chat_postMessage(
                    channel=SLACK_NOTIFICATION_CHANNEL_ID,
                    text=notification_text
                )
            else:
                # Respond in a thread to the original message if no specific channel is set
                logger.info(f"Replying in thread to message {message_ts} in channel {channel_id} (msg_id: {message_id})")
                if not message_ts: # Should always be there for actual messages
                     logger.warning(f"Message {message_id} from {user_id} is missing 'ts'. Cannot reply in thread. Sending to channel.")
                     say(text=notification_text) # Send to channel if no ts
                else:
                     say(text=notification_text, thread_ts=message_ts)
            logger.info(f"Sent moderation notification for user <@{user_id}> (msg_id: {message_id}).")
        except Exception as e:
            logger.exception(f"Error sending Slack notification for msg_id {message_id} from user <@{user_id}>: {e}")
            # Fallback: Print to console if say/chat_postMessage fails
            # logger.error(f"Fallback Notification (Error: {e}): {notification_text}") # Already logged by exception
    else:
        flag_status = "flagged by OpenAI (but not for locally specified categories)" if moderation_result.flagged else "clean"
        flagged_categories_by_openai = [
            cat.replace('_', '/') for cat, val in moderation_result.categories.__dict__.items() if val
        ]
        details = f"(OpenAI overall_flagged: {moderation_result.flagged}. OpenAI Categories: {flagged_categories_by_openai if moderation_result.flagged else 'None'})"
        logger.info(f"Message from <@{user_id}> in <#{channel_id}> (msg_id: {message_id}) determined {flag_status} by local policy. {details} Text: \"{text_to_moderate[:50]}...\"")


# Register the message handler only if app was initialized
if app:
    register_message_handler(app, message_moderation_handler)
else:
    logger.critical("CRITICAL ERROR: Slack app not initialized. Cannot register message handler.")

# Main execution block
if __name__ == "__main__":
    logger.info("Starting application...")
    # Essential keys (SLACK_BOT_TOKEN, SLACK_APP_TOKEN, OPENAI_API_KEY) are checked in config.py.
    # If any are missing, config.py would have raised ValueError and stopped execution.
    # create_slack_app also logs if it fails due to missing SLACK_BOT_TOKEN.
    
    if not app:
        # This is a fallback, as config.py or create_slack_app should have already handled this.
        logger.critical("Application cannot start: Slack app failed to initialize. Check SLACK_BOT_TOKEN.")
    elif not SLACK_APP_TOKEN: # Specifically for SocketModeHandler, also checked by config.py
        logger.critical("Application cannot start: SLACK_APP_TOKEN is not configured. SocketModeHandler requires it.")
    else:
        logger.info("Starting Slack SocketModeHandler...")
        try:
            SocketModeHandler(app, SLACK_APP_TOKEN).start() # SLACK_APP_TOKEN from config
        except Exception as e:
            logger.critical(f"Failed to start SocketModeHandler: {e}", exc_info=True)
            logger.critical("Ensure SLACK_APP_TOKEN is correct and the Slack App is configured for Socket Mode in its settings.")
