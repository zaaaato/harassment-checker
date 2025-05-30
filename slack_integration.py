import logging # Import logging
from slack_bolt import App
# SocketModeHandler might be needed if __main__ is used for actual connection
# from slack_bolt.adapter.socket_mode import SocketModeHandler 
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN # Import tokens from config

logger = logging.getLogger(__name__) # Get a logger instance

def create_slack_app():
    """
    Initializes and returns a Slack App instance using SLACK_BOT_TOKEN from config.
    """
    if not SLACK_BOT_TOKEN:
        # This case is technically handled by config.py raising an error,
        # but as a safeguard for this module's direct use:
        logger.critical("SLACK_BOT_TOKEN is not configured. Cannot create Slack app.")
        return None
    app = App(token=SLACK_BOT_TOKEN)
    logger.info("Slack App initialized successfully.")
    return app

def register_message_handler(app, handler_function):
    """
    Registers the provided handler_function to listen to all message events.
    The 'message' event provides 'message' and 'say' arguments to its listeners.
    """
    if not app: # Add a check for app
        logger.error("Slack app instance is None. Cannot register message handler.")
        return

    @app.message("") # Listen to all messages (empty string regex)
    def message_wrapper(message, say):
        try:
            handler_function(message, say)
        except Exception as e:
            logger.exception(f"Error in Slack message handler (wrapped by @app.message): {e}")
            # Optionally, inform the user or channel about the error if appropriate
            # try:
            #     say("An unexpected error occurred while processing your message. Please try again later.")
            # except Exception as say_error:
            #     logger.error(f"Failed to send error message to Slack: {say_error}")


# Example (optional, for basic testing of this file if run directly):
if __name__ == "__main__":
    # This block is for basic validation or testing of this module only.
    # For the full app, run app.py.
    
    # To ensure config.py's logging (and .env loading) happen:
    try:
        # Attempt to import a variable that would cause config.py to execute and validate.
        import config # Trigger config.py load and validation
        logger.info("Config loaded via import for slack_integration.py's __main__ test.")
    except ValueError as e:
        logger.critical(f"Configuration error from config.py: {e}")
        logger.info("slack_integration.py __main__ tests cannot proceed without valid config.")
        exit(1) # Exit if essential config is missing

    logger.info("Attempting to initialize Slack App for basic check...")
    
    # SLACK_BOT_TOKEN and SLACK_APP_TOKEN are already imported from config
    if not SLACK_BOT_TOKEN:
        # This is already logged by create_slack_app, but good for __main__ context too
        logger.error("SLACK_BOT_TOKEN not found in config. Cannot initialize app for __main__ test.")
    # SLACK_APP_TOKEN would be needed if we were to start SocketModeHandler here
    elif not SLACK_APP_TOKEN: 
        logger.warning("SLACK_APP_TOKEN not found in config. Socket Mode would not work if started here.")
        # Initialize the app for basic checks even if app_token is missing for SocketModeHandler
        app_instance = create_slack_app()
        if app_instance:
            logger.info("Slack App initialized with Bot Token (from config) for __main__ test.")
            logger.info("This is a basic check. Full app functionality is in app.py.")
        else:
            logger.error("Failed to initialize Slack App in __main__.")
    else:
        app_instance = create_slack_app()
        if app_instance:
            logger.info("Slack App initialized successfully using tokens from config for __main__ test.")
            logger.info("To actually run and connect, SocketModeHandler would be needed here,")
            logger.info("but this script is for module testing. Run app.py for the full application.")
            # Example if you wanted to test connection (requires SLACK_APP_TOKEN):
            # logger.info("Attempting to start SocketModeHandler for a brief test (will hang if not stopped)...")
            # handler = SocketModeHandler(app_instance, SLACK_APP_TOKEN)
            # handler.start() # This would block unless run in a thread or stopped
        else:
            logger.error("Failed to initialize Slack App in __main__.")
