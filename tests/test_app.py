import unittest
from unittest.mock import patch, MagicMock, ANY
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock environment variables *before* config and app are imported for the first time.
# This is crucial because config.py reads os.environ when it's loaded.
MOCK_ENV_VARS = {
    'SLACK_BOT_TOKEN': 'xoxb-app-test-bot-token',
    'SLACK_APP_TOKEN': 'xapp-app-test-app-token',
    'OPENAI_API_KEY': 'sk-app-test-openai-key',
    'LOGGING_LEVEL': 'CRITICAL', # Minimize log noise during tests
    'SLACK_NOTIFICATION_CHANNEL_ID': '' # Default to empty for most tests
}

# Apply mock environment variables. This will affect subsequent imports of config.
# The 'clear=True' ensures only these env vars are seen by the modules during import.
@patch.dict(os.environ, MOCK_ENV_VARS, clear=True)
def load_app_module():
    """Helper function to load (or reload) app.py after mocks are in place."""
    # If app.py was already imported, we need to reload it to see mocked env vars effect on config.
    if 'app' in sys.modules:
        import importlib
        importlib.reload(sys.modules['config']) # Reload config first
        return importlib.reload(sys.modules['app'])
    else:
        import app # First time import
        return app

# Load the app module once with mocked environment variables for the test class
# This ensures that config.py (imported by app.py) uses these mocked values.
app_module = load_app_module()
message_moderation_handler = app_module.message_moderation_handler


# Now, prepare patches for dependencies that are directly used by app.py's functions.
# We are patching them within the app_module's namespace.
@patch.dict(os.environ, MOCK_ENV_VARS, clear=True) # Ensure env vars for each test method if needed
@patch(f'{app_module.__name__}.moderate_text') # Mocks openai_integration.moderate_text as used in app.py
@patch(f'{app_module.__name__}.app', new_callable=MagicMock) # Mocks the global 'app' instance in app.py
class TestApp(unittest.TestCase):

    def setUp(self):
        # Reset mocks for each test to ensure test isolation
        # The global 'app' mock (mock_global_app_instance) needs its client attribute reset or re-mocked if used by tests.
        # mock_global_app_instance is the MagicMock from @patch(f'{app_module.__name__}.app', new_callable=MagicMock)
        # Its client attribute will be used by test_message_handler_with_harassment_dedicated_channel
        
        # The HARASSMENT_CATEGORIES for tests
        self.test_harassment_categories = ['harassment', 'hate']
        # Patch HARASSMENT_CATEGORIES in the config module directly for the duration of the test method
        # or ensure app_module.HARASSMENT_CATEGORIES is what you expect.
        # For simplicity, we'll assume app_module.HARASSMENT_CATEGORIES gets the value from the
        # initially loaded config (which is affected by MOCK_ENV_VARS).
        # If a test needs specific categories, it can patch app_module.HARASSMENT_CATEGORIES.
        app_module.HARASSMENT_CATEGORIES = self.test_harassment_categories
        app_module.SLACK_NOTIFICATION_CHANNEL_ID = '' # Default for most tests


    def test_message_handler_no_harassment(self, mock_global_app_instance, mock_moderate_text):
        mock_say = MagicMock()
        mock_message = {'text': 'This is a clean message.', 'user': 'U123', 'channel': 'C123', 'ts': '12345.67890'}
        
        mock_moderation_result = MagicMock()
        mock_moderation_result.flagged = False
        # Setup categories on the result mock
        mock_categories_obj = MagicMock()
        for cat in self.test_harassment_categories: # Use categories defined in setUp
            setattr(mock_categories_obj, cat, False)
        mock_moderation_result.categories = mock_categories_obj
        mock_moderate_text.return_value = mock_moderation_result

        message_moderation_handler(mock_message, mock_say)

        mock_moderate_text.assert_called_once_with('This is a clean message.')
        mock_say.assert_not_called() 

    def test_message_handler_with_harassment_threaded_reply(self, mock_global_app_instance, mock_moderate_text):
        mock_say = MagicMock()
        mock_message = {'text': 'This is harassment!', 'user': 'U123', 'channel': 'C123', 'ts': '12345.67890'}

        mock_moderation_result = MagicMock()
        mock_moderation_result.flagged = True
        mock_categories_obj = MagicMock()
        setattr(mock_categories_obj, 'harassment', True)
        setattr(mock_categories_obj, 'hate', False)
        mock_moderation_result.categories = mock_categories_obj
        mock_moderate_text.return_value = mock_moderation_result
        
        # Ensure SLACK_NOTIFICATION_CHANNEL_ID is None/empty for this test
        app_module.SLACK_NOTIFICATION_CHANNEL_ID = '' 

        message_moderation_handler(mock_message, mock_say)

        mock_moderate_text.assert_called_once_with('This is harassment!')
        # Original message link construction in app.py: f"slack://channel/{channel_id}/p{message_ts.replace('.', '')}"
        expected_link = f"slack://channel/C123/p1234567890"
        expected_notification_text = (
            f":warning: Message from <@U123> in <#C123> flagged for: *harassment*.\n"
            f"> Original message: <{expected_link}>\n"
            f"> _{mock_message['text']}_"
        )
        mock_say.assert_called_once_with(text=expected_notification_text, thread_ts=mock_message['ts'])

    def test_message_handler_with_harassment_dedicated_channel(self, mock_global_app_instance, mock_moderate_text):
        # mock_global_app_instance is the MagicMock for the app.app object
        # We need to mock its 'client' attribute
        mock_slack_client = MagicMock()
        mock_global_app_instance.client = mock_slack_client # Configure the client on the mocked app

        mock_say = MagicMock() 
        mock_message = {'text': 'This is hate speech!', 'user': 'U123', 'channel': 'C123', 'ts': '12345.67890'}

        mock_moderation_result = MagicMock()
        mock_moderation_result.flagged = True
        mock_categories_obj = MagicMock()
        setattr(mock_categories_obj, 'harassment', False)
        setattr(mock_categories_obj, 'hate', True)
        mock_moderation_result.categories = mock_categories_obj
        mock_moderate_text.return_value = mock_moderation_result

        # Set SLACK_NOTIFICATION_CHANNEL_ID for this test
        test_notification_channel = 'C_NOTIFY_CHANNEL'
        app_module.SLACK_NOTIFICATION_CHANNEL_ID = test_notification_channel

        message_moderation_handler(mock_message, mock_say)

        mock_moderate_text.assert_called_once_with('This is hate speech!')
        mock_say.assert_not_called()
        
        expected_link = f"slack://channel/C123/p1234567890"
        expected_notification_text = (
            f":warning: Message from <@U123> in <#C123> flagged for: *hate*.\n"
            f"> Original message: <{expected_link}>\n"
            f"> _{mock_message['text']}_"
        )
        mock_slack_client.chat_postMessage.assert_called_once_with(
            channel=test_notification_channel,
            text=expected_notification_text
        )

    def test_message_handler_empty_text(self, mock_global_app_instance, mock_moderate_text):
        mock_say = MagicMock()
        mock_message = {'text': '', 'user': 'U123', 'channel': 'C123', 'ts': '12345.67890'} 

        message_moderation_handler(mock_message, mock_say)
        mock_moderate_text.assert_not_called()
        mock_say.assert_not_called()

    def test_message_handler_moderation_api_error(self, mock_global_app_instance, mock_moderate_text):
        mock_say = MagicMock()
        mock_message = {'text': 'Test message', 'user': 'U123', 'channel': 'C123', 'ts': '12345.67890'}
        
        mock_moderate_text.return_value = None # Simulate error from moderate_text

        message_moderation_handler(mock_message, mock_say)
        
        mock_moderate_text.assert_called_once_with('Test message')
        mock_say.assert_not_called()

if __name__ == '__main__':
    unittest.main()
