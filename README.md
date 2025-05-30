# Slack Moderation Bot

This bot monitors Slack messages and uses the OpenAI Moderation API to detect and notify about potentially harassing content.

## Features

*   Monitors messages in channels it's invited to within a Slack workspace.
*   Uses OpenAI's Moderation API for content analysis.
*   Flags messages based on a configurable list of categories (e.g., harassment, hate speech).
*   Sends notifications to a designated Slack channel or as a threaded reply to the original message.
*   Configuration via environment variables (supports `.env` file).
*   Structured logging for monitoring and debugging.

## Project Structure

```
.
├── app.py                   # Main application logic, message handling, and Socket Mode runner
├── config.py                # Configuration loading (from .env), logging setup, harassment categories
├── openai_integration.py    # Handles OpenAI API communication
├── slack_integration.py     # Handles Slack Bolt app setup and message registration
├── requirements.txt         # Python dependencies
├── .env.example             # Example environment file for local development
└── README.md                # This file
```

## Prerequisites

*   Python 3.8+
*   A Slack workspace where you have permissions to create and install apps.
*   An OpenAI API key with access to the Moderation API.

## Setup Instructions

### 1. Clone the Repository

If you have access to the repository, clone it. Otherwise, ensure you have the project files.
```bash
# Example:
# git clone <your_repository_url>
# cd <repository_directory_name>
```

### 2. Create a Slack App

1.  Go to [https://api.slack.com/apps](https://api.slack.com/apps) and click "Create New App".
2.  Choose "From scratch".
3.  Name your app (e.g., "Moderation Bot") and select your workspace. Click "Create App".
4.  **Add Bot Token Scopes**:
    *   In the sidebar of your app's settings page, navigate to "OAuth & Permissions".
    *   Scroll down to "Scopes" > "Bot Token Scopes".
    *   Click "Add an OAuth Scope" and add the following:
        *   `chat:write` (to send messages and notifications)
        *   `channels:history` (to read messages in public channels the bot is in)
        *   `groups:history` (to read messages in private channels the bot is invited to)
        *   `mpim:history` (to read messages in group DMs the bot is invited to)
        *   `im:history` (to read DMs the bot is part of, if direct messaging is intended)
        *   `channels:read` (to get channel names, useful for logging/notifications if bot joins/leaves channels)
        *   `users:read` (optional, to resolve user mentions to names - may not be strictly needed by current features but good for future enhancements)
5.  **Install App to Workspace**:
    *   Still in "OAuth & Permissions", scroll up and click "Install to Workspace".
    *   Follow the prompts to authorize the app.
    *   After installation, copy the **Bot User OAuth Token** (starts with `xoxb-`). This is your `SLACK_BOT_TOKEN`.
6.  **Enable Socket Mode and Generate an App-Level Token**:
    *   In the sidebar, navigate to "Basic Information".
    *   Scroll down to "App-Level Tokens".
    *   Click "Generate Token and Scopes".
    *   Give your token a name (e.g., `socket-mode-token`) and add the `connections:write` scope. Click "Generate".
    *   Copy this token (starts with `xapp-`). This is your `SLACK_APP_TOKEN`.
    *   Navigate to "Socket Mode" in the sidebar (under "Settings").
    *   Enable Socket Mode by toggling the switch. You should see your `xapp-` token listed.
7.  **Invite the Bot to Channels**:
    *   In your Slack client, invite the bot user (e.g., "@Moderation Bot") to any public or private channels you want it to monitor. The bot will only process messages in channels it is a member of.

### 3. Obtain an OpenAI API Key

1.  Go to [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys).
2.  Log in or sign up for an OpenAI account.
3.  Click "Create new secret key".
4.  Copy the generated key. This is your `OPENAI_API_KEY`. Store it securely.

### 4. Set Up Environment Variables

1.  In the root directory of the project, create a file named `.env` (e.g., by copying `.env.example`):
    ```bash
    cp .env.example .env
    ```
2.  Edit the `.env` file with the tokens and keys you obtained:
    ```ini
    SLACK_BOT_TOKEN="xoxb-your-bot-user-oauth-token"
    SLACK_APP_TOKEN="xapp-your-app-level-socket-mode-token"
    OPENAI_API_KEY="sk-your-openai-api-key"

    # Optional: Specify a channel ID to send all notifications to.
    # If commented out or empty, notifications will be sent as threaded replies
    # in the channel where the original message was posted.
    # Find a channel's ID by right-clicking it in Slack and choosing "Copy Link",
    # then extracting the ID (starts with C) from the URL.
    # Example: SLACK_NOTIFICATION_CHANNEL_ID="C0123ABCXYZ"

    # Optional: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    # Defaults to INFO if not set.
    # Example: LOGGING_LEVEL="DEBUG"
    ```
    Replace the placeholder values with your actual credentials.

### 5. Install Dependencies

Ensure you have Python 3.8+ installed. It's recommended to use a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```
Then install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

Once the setup is complete, you can run the bot:
```bash
python app.py
```
The bot will connect to Slack using Socket Mode. You should see log messages in your console indicating it has started and is listening for messages.

To stop the bot, press `Ctrl+C` in the console.

## Running Unit Tests

Unit tests are located in the `tests/` directory. To run them:
```bash
python -m unittest discover -s tests
```
This command will discover and run all tests within the `tests` directory. Make sure you have any required environment variables set if your test setup relies on them (though ideally, tests should mock external services and configurations).

*(Further tests for other modules like `slack_integration.py` and `app.py` will be added in the future.)*

## Configuration Variables

The application uses the following environment variables, typically set in the `.env` file:

*   `SLACK_BOT_TOKEN` (Required): Your Slack Bot User OAuth Token (starts with `xoxb-`).
*   `SLACK_APP_TOKEN` (Required): Your Slack App-Level Token for Socket Mode (starts with `xapp-`).
*   `OPENAI_API_KEY` (Required): Your OpenAI API key (starts with `sk-`).
*   `SLACK_NOTIFICATION_CHANNEL_ID` (Optional): If set, all moderation notifications will be sent to this specific Slack channel ID. If not set or commented out, notifications are sent as threaded replies to the original message in the channel where it was posted.
*   `LOGGING_LEVEL` (Optional): Sets the application's logging level. Defaults to `INFO`. Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

## Harassment Categories

The bot currently checks for the following OpenAI Moderation API categories. These are defined in `config.py` and are based on the attributes available from the OpenAI SDK's moderation response:
```python
# Located in config.py
HARASSMENT_CATEGORIES = [
    'harassment',
    'harassment_threatening',
    'hate',
    'hate_threatening',
    'self_harm',
    'self_harm_intent',
    'self_harm_instructions',
    'sexual',
    'sexual_minors',
    'violence',
    'violence_graphic'
]
```
This list can be modified directly in `config.py` if you wish to focus on a different set of categories provided by the OpenAI Moderation API.
```
