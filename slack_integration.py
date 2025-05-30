"""
Manages Slack API connection, app initialization, and event handling registration
for the moderation bot.

This module provides functions to:
- Create and configure a Slack Bolt App instance.
- Register handlers for Slack message events.
"""
import logging
from slack_bolt import App
# SLACK_APP_TOKEN is imported for the __main__ block example, not directly by core functions here.
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN 

logger = logging.getLogger(__name__)

def create_slack_app():
    """
    Initializes and returns a Slack Bolt App instance.

    This function relies on the `SLACK_BOT_TOKEN` being available in the application's
    configuration (loaded via `config.py`). The Bolt App instance is the central
    object for interacting with the Slack API (e.g., receiving events, sending messages).

    Returns:
        slack_bolt.App: An initialized instance of the Slack Bolt App.
                        Returns None if SLACK_BOT_TOKEN is not configured, although
                        config.py should raise a ValueError before this happens.
    """
    if not SLACK_BOT_TOKEN:
        # This check is a safeguard. config.py is expected to raise a ValueError
        # if SLACK_BOT_TOKEN is missing, which would halt execution before this point.
        logger.critical("SLACK_BOT_TOKEN is not configured. Cannot create Slack app.")
        return None
    
    # Initialize the Slack Bolt App with the bot token.
    app = App(token=SLACK_BOT_TOKEN)
    logger.info("Slack Bolt App initialized successfully with SLACK_BOT_TOKEN.")
    return app

def register_message_handler(app: App, handler_function):
    """
    Registers a given function to handle incoming Slack message events.

    This function uses the `@app.message("")` decorator pattern from Slack Bolt
    to listen to all messages in channels where the bot is present. The provided
    `handler_function` will be called when a new message is received.

    Args:
        app (slack_bolt.App): The initialized Slack Bolt App instance to register the handler with.
        handler_function (callable): The function to be executed when a message event occurs.
                                     This function should typically accept `message` and `say`
                                     arguments, as provided by Slack Bolt.
    """
    if not app:
        logger.error("Slack app instance is None. Cannot register message handler.")
        return

    # The @app.message("") decorator listens to all non-subtype messages.
    # An empty string "" as the pattern matches all messages.
    # Slack Bolt passes 'message' (payload) and 'say' (utility function) to the wrapped handler.
    @app.message("") 
    def message_wrapper(message, say):
        # This wrapper ensures that any exceptions within the user-provided handler_function
        # are caught and logged, preventing them from crashing the main app event loop.
        try:
            handler_function(message, say)
        except Exception as e:
            logger.exception(f"Error occurred in the registered message handler: {e}")
            # Optionally, could send a generic error message to Slack via `say` if appropriate,
            # but be cautious of error loops or revealing too much detail.
            # try:
            #     say(text="An unexpected error occurred while processing your message. The admin has been notified.")
            # except Exception as say_error:
            #     logger.error(f"Failed to send error message to Slack channel: {say_error}")

    logger.info(f"Message handler '{handler_function.__name__}' registered successfully to listen to all messages.")


# This block is for basic validation or direct testing of this module's functions.
# It's not intended for running the full application (that's done via app.py).
if __name__ == "__main__":
    # Ensure config.py is loaded to set up logging and make environment variables available.
    try:
        import config # This will execute config.py, including logging setup and env var loading.
        logger.info("Config module loaded successfully for slack_integration.py direct execution.")
    except ValueError as e:
        # This typically happens if essential API keys are missing in .env or environment.
        logger.critical(f"Failed to load config due to missing environment variables: {e}")
        logger.warning("Cannot run slack_integration.py __main__ block without essential API keys.")
        exit(1) # Exit because the module's functions might not behave as expected.

    logger.info("--- Slack Integration Direct Test ---")
    logger.info("Attempting to initialize Slack App for basic check...")
    
    # Check if SLACK_BOT_TOKEN is available (it should be, due to config.py import).
    if not SLACK_BOT_TOKEN:
        logger.error("SLACK_BOT_TOKEN is still not found after config import. This should not happen if config is correct.")
    else:
        # Test creating the app instance.
        app_instance = create_slack_app()
        if app_instance:
            logger.info("slack_integration.create_slack_app() executed successfully in __main__.")
            
            # Dummy handler for testing registration
            def _dummy_test_handler(message, say):
                logger.info(f"__main__ _dummy_test_handler called with message: {message.get('text')}")
            
            register_message_handler(app_instance, _dummy_test_handler)
            logger.info("slack_integration.register_message_handler() called in __main__.")
            logger.info("Note: This does not start the Slack connection or event listeners.")
            logger.info("To run the full bot and connect to Slack, execute app.py.")

            # If SLACK_APP_TOKEN is also set, one could theoretically start SocketModeHandler here for a deeper test,
            # but that would make this script block and try to connect to Slack.
            if SLACK_APP_TOKEN:
                logger.info("SLACK_APP_TOKEN is also configured.")
                logger.info("For a full test with SocketModeHandler, run app.py.")
            else:
                logger.warning("SLACK_APP_TOKEN is not configured. Full app execution via app.py would require it for Socket Mode.")
        else:
            logger.error("Failed to create Slack App instance in __main__ direct execution.")
    logger.info("--- End of Slack Integration Direct Test ---")
