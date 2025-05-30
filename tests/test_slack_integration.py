import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Attempt to import the modules to be tested.
# This might be problematic if config.py (imported by slack_integration)
# raises errors due to missing environment variables not set during tests.
try:
    from slack_integration import create_slack_app, register_message_handler
    # We need to patch 'App' where it's looked up by slack_integration.
    # If slack_integration.py has 'from slack_bolt import App', then we patch 'slack_integration.App'.
    # If it has 'import slack_bolt; slack_bolt.App()', then we patch 'slack_bolt.App'.
    # Current slack_integration.py: 'from slack_bolt import App' -> patch 'slack_integration.App'
except ImportError as e:
    print(f"Failed to import modules from slack_integration: {e}")
    print("This might be due to issues with sys.path or dependencies.")
    # Define placeholders if import fails, so tests can be skipped or structure remains valid
    create_slack_app = None
    register_message_handler = None
except ValueError as e: # Raised by config.py if essential ENV VARS are missing
    print(f"Note: Failed to import from slack_integration due to config validation: {e}")
    print("This is expected if SLACK_BOT_TOKEN etc. are not set for the test environment.")
    create_slack_app = None
    register_message_handler = None


# Mock config variables that slack_integration might use.
# These are applied via @patch.dict to 'config.__dict__' or 'slack_integration.config.__dict__'
# depending on how slack_integration imports config.
# If 'from config import SLACK_BOT_TOKEN', then 'slack_integration.SLACK_BOT_TOKEN' needs patching,
# or more broadly, 'config.SLACK_BOT_TOKEN'. Patching 'config' is cleaner.
MOCK_CONFIG_VALUES = {
    'SLACK_BOT_TOKEN': 'xoxb-test-bot-token-for-slack-integration-tests',
    'SLACK_APP_TOKEN': 'xapp-test-app-token-for-slack-integration-tests',
    # Add other config vars if slack_integration directly uses them.
}

# We patch 'config' as it's imported by 'slack_integration'
# The goal is that when slack_integration accesses config.SLACK_BOT_TOKEN, it gets our mock value.
# However, slack_integration.py does: from config import SLACK_BOT_TOKEN
# So, we need to patch slack_integration.SLACK_BOT_TOKEN directly or ensure config module itself is patched
# before slack_integration tries to import from it.
# A common way: @patch('slack_integration.SLACK_BOT_TOKEN', MOCK_CONFIG_VALUES['SLACK_BOT_TOKEN']) for each var.
# Or, patch 'config' module that slack_integration imports.
# Let's try patching the 'config' module that slack_integration sees.

@patch.dict(os.environ, {
    'SLACK_BOT_TOKEN': MOCK_CONFIG_VALUES['SLACK_BOT_TOKEN'],
    'SLACK_APP_TOKEN': MOCK_CONFIG_VALUES['SLACK_APP_TOKEN'],
    'OPENAI_API_KEY': 'sk-dummy-key-for-tests', # Required by config.py not to raise error
    'LOGGING_LEVEL': 'CRITICAL', # To minimize log output during tests
}, clear=True)
class TestSlackIntegration(unittest.TestCase):

    def setUp(self):
        # Reload slack_integration to ensure it picks up patched config/env vars
        # This is a bit heavy-handed but can be necessary if modules cache imported values at load time.
        # For now, let's assume direct patching of where App is looked up works.
        if create_slack_app is None or register_message_handler is None:
            self.skipTest("Skipping slack_integration tests due to import failure.")

    @patch('slack_integration.App') # Mocks 'App' in the slack_integration module's namespace
    def test_create_slack_app_initializes_app_with_token(self, MockSlackBoltApp):
        # MockApp is the class 'slack_bolt.App'
        # MockApp.return_value is the instance of the app
        mock_app_instance = MockSlackBoltApp.return_value 
        
        app = create_slack_app()

        # Assert that slack_bolt.App was initialized with the token from MOCK_CONFIG
        MockSlackBoltApp.assert_called_once_with(token=MOCK_CONFIG_VALUES['SLACK_BOT_TOKEN'])
        # Assert that the function returned the created app instance
        self.assertEqual(app, mock_app_instance, "create_slack_app should return the app instance created by slack_bolt.App")

    @patch('slack_integration.App') # Mock App again if needed, or pass mock_app_instance
    def test_register_message_handler_uses_app_message_decorator(self, MockSlackBoltApp):
        # We need a mock instance of the App class for this test
        mock_app_object = MagicMock() # This represents an instance of App()
        # The app instance should have a 'message' method which is a decorator
        # This decorator method should also be a MagicMock to track its calls
        mock_app_object.message = MagicMock()
        # When mock_app_object.message("some_regex") is called, it returns a decorator function.
        # This decorator function, when called with the handler, should also be tracked.
        # So, mock_app_object.message.return_value should be a mock (the decorator itself).
        mock_decorator = MagicMock()
        mock_app_object.message.return_value = mock_decorator

        dummy_handler_function = MagicMock() # A dummy function to be registered

        register_message_handler(mock_app_object, dummy_handler_function)

        # 1. Assert that app.message decorator was called with the correct regex (empty string for all messages)
        mock_app_object.message.assert_called_once_with("")
        
        # 2. Assert that the decorator returned by app.message (which is mock_decorator)
        #    was called with a function (the wrapper that calls our dummy_handler_function).
        self.assertTrue(mock_decorator.called, "The decorator returned by app.message should have been called.")
        
        # Check that the function passed to the decorator (the wrapper) is callable
        args, _ = mock_decorator.call_args
        self.assertTrue(callable(args[0]), "A callable function (the wrapper) should be passed to the decorator.")

        # (Optional) Test the wrapper behavior:
        # If you want to test that the dummy_handler_function is called by the wrapper:
        # registered_wrapper_function = mock_decorator.call_args[0][0] # Get the wrapper
        # mock_say = MagicMock()
        # mock_message_payload = {'text': 'hello'}
        # registered_wrapper_function(message=mock_message_payload, say=mock_say)
        # dummy_handler_function.assert_called_once_with(message=mock_message_payload, say=mock_say)


if __name__ == '__main__':
    unittest.main()
