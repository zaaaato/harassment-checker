import os
from dotenv import load_dotenv

# Load environment variables from .env file at the very beginning
load_dotenv()

# API Keys and Tokens
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN") # For Socket Mode
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Optional: Specific channel for notifications
SLACK_NOTIFICATION_CHANNEL_ID = os.environ.get("SLACK_NOTIFICATION_CHANNEL_ID")

# Moderation settings
# These are the string representations that the OpenAI API uses for categories.
# The SDK then converts these to attributes by replacing '/' with '_',
# e.g., 'harassment/threatening' becomes 'harassment_threatening'.
HARASSMENT_CATEGORIES = [
    'harassment',
    'harassment_threatening', # Was 'harassment/threatening'
    'hate',
    'hate_threatening', # Was 'hate/threatening'
    'self_harm', # Was 'self-harm'
    'self_harm_intent', # Was 'self-harm/intent'
    'self_harm_instructions', # Was 'self-harm/instructions'
    'sexual',
    'sexual_minors', # Was 'sexual/minors'
    'violence',
    'violence_graphic' # Was 'violence/graphic'
]

# Validate essential configurations
if not SLACK_BOT_TOKEN:
    raise ValueError("Missing SLACK_BOT_TOKEN in .env file or environment.")
if not SLACK_APP_TOKEN:
    raise ValueError("Missing SLACK_APP_TOKEN for SocketModeHandler in .env file or environment.")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file or environment.")

import logging

# Logging Configuration
LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOGGING_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Optional: Print loaded config for verification during startup (can be removed in production)
logger.info("Configuration loaded:")
logger.info(f"  SLACK_BOT_TOKEN: {'Set' if SLACK_BOT_TOKEN else 'Not Set'}")
logger.info(f"  SLACK_APP_TOKEN: {'Set' if SLACK_APP_TOKEN else 'Not Set'}")
logger.info(f"  OPENAI_API_KEY: {'Set' if OPENAI_API_KEY else 'Not Set'}")
logger.info(f"  SLACK_NOTIFICATION_CHANNEL_ID: {SLACK_NOTIFICATION_CHANNEL_ID if SLACK_NOTIFICATION_CHANNEL_ID else 'Not Set (will reply in thread/channel)'}")
logger.info(f"  HARASSMENT_CATEGORIES: {HARASSMENT_CATEGORIES}")
logger.info(f"  LOGGING_LEVEL: {LOGGING_LEVEL}")
