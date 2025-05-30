"""
Handles application configuration by loading settings from environment variables.
It supports loading from a .env file for local development and performs
validation for essential API keys. It also configures basic logging for the application.
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists.
# This is useful for local development. In production, variables are typically set directly.
load_dotenv()

# --- API Keys and Tokens ---
# SLACK_BOT_TOKEN: OAuth token for the Slack bot user. Required for most bot operations.
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
# SLACK_APP_TOKEN: App-level token for Slack Socket Mode. Required for Socket Mode connection.
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
# OPENAI_API_KEY: API key for OpenAI services. Required for accessing the Moderation API.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- Notification Settings ---
# SLACK_NOTIFICATION_CHANNEL_ID: Optional Slack channel ID where moderation notifications will be sent.
# If not set, notifications are sent as threaded replies in the channel of the original message.
SLACK_NOTIFICATION_CHANNEL_ID = os.environ.get("SLACK_NOTIFICATION_CHANNEL_ID")

# --- Moderation Settings ---
# HARASSMENT_CATEGORIES: A list of OpenAI Moderation API category names (attribute-style)
# that the application will specifically look for to flag content.
# These correspond to boolean attributes on the OpenAI SDK's category object (e.g., result.categories.harassment).
HARASSMENT_CATEGORIES = [
    'harassment',               # Content that expresses abusive content targeting individuals or groups.
    'harassment_threatening',  # Harassment that also includes threatening language.
    'hate',                     # Content that expresses, incites, or promotes hate based on protected characteristics.
    'hate_threatening',       # Hate speech that also includes threatening language.
    'self_harm',                # Content that promotes, encourages, or depicts acts of self-harm.
    'self_harm_intent',         # Content where the user expresses intent to self-harm.
    'self_harm_instructions',   # Content that provides instructions on how to self-harm.
    'sexual',                   # Content meant to arouse sexual excitement, such as depictions of sexual activity.
    'sexual_minors',            # Sexual content that includes minors.
    'violence',                 # Content that promotes or glorifies violence or celebrates the suffering or humiliation of others.
    'violence_graphic'          # Graphic violence, including depictions of death, gore, or extreme violence.
]

# --- Logging Configuration ---
# LOGGING_LEVEL: Determines the minimum severity level of messages to log.
# Defaults to "INFO" if not set in the environment.
LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL", "INFO").upper()

# Configure basic logging for the entire application.
# This setup is done once when this module is first imported.
logging.basicConfig(
    level=LOGGING_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', # Log format
    datefmt='%Y-%m-%d %H:%M:%S'  # Date format for log entries
)
# Get a logger for this module (config.py)
logger = logging.getLogger(__name__)


# --- Essential Configuration Validation ---
# It's critical to check for essential API keys at startup.
# If these are missing, the application cannot function correctly.
# Raising ValueError here will stop the application if critical configs are absent.
if not SLACK_BOT_TOKEN:
    logger.critical("CRITICAL: Missing SLACK_BOT_TOKEN in .env file or environment.")
    raise ValueError("Missing SLACK_BOT_TOKEN in .env file or environment.")
if not SLACK_APP_TOKEN:
    logger.critical("CRITICAL: Missing SLACK_APP_TOKEN for SocketModeHandler in .env file or environment.")
    raise ValueError("Missing SLACK_APP_TOKEN for SocketModeHandler in .env file or environment.")
if not OPENAI_API_KEY:
    logger.critical("CRITICAL: Missing OPENAI_API_KEY in .env file or environment.")
    raise ValueError("Missing OPENAI_API_KEY in .env file or environment.")

# Log the loaded configuration for verification (excluding sensitive parts of keys if necessary in future).
logger.info("Configuration loaded successfully.")
logger.info(f"  SLACK_BOT_TOKEN: {'Set' if SLACK_BOT_TOKEN else 'Not Set'}")
logger.info(f"  SLACK_APP_TOKEN: {'Set' if SLACK_APP_TOKEN else 'Not Set'}")
logger.info(f"  OPENAI_API_KEY: {'Set' if OPENAI_API_KEY else 'Not Set'}")
logger.info(f"  SLACK_NOTIFICATION_CHANNEL_ID: {SLACK_NOTIFICATION_CHANNEL_ID if SLACK_NOTIFICATION_CHANNEL_ID else 'Not Set (will reply in thread/channel)'}")
# logger.debug(f"  HARASSMENT_CATEGORIES: {HARASSMENT_CATEGORIES}") # Debug as it can be long
logger.info(f"  LOGGING_LEVEL: {LOGGING_LEVEL}")
