import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add project root to sys.path to allow importing project modules
# This assumes 'tests' is a subdirectory of the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now try to import. If config.py raises ValueError due to missing env vars for tests,
# this import might fail. For robust testing, critical env vars might need to be mocked or set.
# For now, we assume they might be set in a test environment or config.py handles their absence gracefully for imports.
try:
    from openai_integration import moderate_text, client as openai_client # import client for one test
    import openai # For exception types like openai.APIError, openai.AuthenticationError
except ValueError as e:
    print(f"Note: Failed to import openai_integration due to config validation: {e}")
    print("This might be expected if essential ENV VARS are not set for the test environment.")
    print("Some tests might be skipped or fail if modules cannot be loaded.")
    moderate_text = None # Ensure it's defined for test structure
    openai_client = None
    openai = None # Ensure it's defined

class TestOpenaiIntegration(unittest.TestCase):

    def setUp(self):
        # This check ensures that tests that depend on these modules being loaded are skipped
        # if the initial import failed (e.g. due to missing ENV VARS stopping config.py)
        if moderate_text is None or openai is None:
            self.skipTest("Skipping tests due to failed import of openai_integration or openai, possibly due to missing ENV VARS for config.")

    @patch('openai_integration.client.moderations.create')
    def test_moderate_text_success(self, mock_create):
        mock_moderation_result = MagicMock()
        mock_moderation_result.flagged = True
        # Simulate the structure of categories and category_scores
        # The actual category names in the response are like 'self-harm' not 'self_harm'
        # but the SDK converts them to attributes like 'self_harm'
        mock_moderation_result.categories = MagicMock()
        mock_moderation_result.categories.harassment = True
        mock_moderation_result.categories.hate = False
        # ... add other categories as needed for comprehensive test

        mock_moderation_result.category_scores = MagicMock()
        mock_moderation_result.category_scores.harassment = 0.987
        mock_moderation_result.category_scores.hate = 0.123


        mock_response = MagicMock()
        mock_response.results = [mock_moderation_result] # This is the object that moderate_text should return
        mock_create.return_value = mock_response

        text_to_moderate = "This is some problematic text."
        result = moderate_text(text_to_moderate)

        self.assertIsNotNone(result)
        self.assertTrue(result.flagged)
        self.assertTrue(result.categories.harassment)
        self.assertFalse(result.categories.hate) # Example of checking another category
        mock_create.assert_called_once_with(input=text_to_moderate)

    @patch('openai_integration.client.moderations.create')
    def test_moderate_text_api_error(self, mock_create):
        # Simulate an API error from the openai library
        # Using openai.APIConnectionError as an example, as APIError is a base class.
        mock_create.side_effect = openai.APIConnectionError(request=MagicMock())


        text_to_moderate = "Some text that will trigger an API error."
        result = moderate_text(text_to_moderate)

        self.assertIsNone(result)
        mock_create.assert_called_once_with(input=text_to_moderate)

    @patch('openai_integration.client.moderations.create')
    def test_moderate_text_unexpected_response_empty_results(self, mock_create):
        mock_response = MagicMock()
        mock_response.results = [] # Empty results list
        mock_create.return_value = mock_response

        text_to_moderate = "Another text."
        result = moderate_text(text_to_moderate)
        self.assertIsNone(result)
        mock_create.assert_called_once_with(input=text_to_moderate)

    @patch('openai_integration.client.moderations.create')
    def test_moderate_text_unexpected_response_results_is_none(self, mock_create):
        mock_response = MagicMock()
        mock_response.results = None # Results attribute is None
        mock_create.return_value = mock_response

        text_to_moderate = "Yet another text."
        result = moderate_text(text_to_moderate)
        self.assertIsNone(result)
        mock_create.assert_called_once_with(input=text_to_moderate)
    
    def test_moderate_text_empty_input_string(self):
        # Test that providing an empty string to moderate_text returns None
        # as per the check `if not text_to_moderate:`
        result = moderate_text("")
        self.assertIsNone(result)

    def test_moderate_text_none_input_string(self):
        # Test that providing None to moderate_text returns None
        result = moderate_text(None)
        self.assertIsNone(result)

    # This test checks the behavior if the global 'client' in openai_integration were None.
    # It requires careful patching of the 'client' object within the 'openai_integration' module.
    @patch('openai_integration.client', None)
    def test_moderate_text_client_is_none(self):
        # This simulates a scenario where the OpenAI client failed to initialize and is None.
        # The moderate_text function has a check: `if not client:`
        text_to_moderate = "Some text."
        result = moderate_text(text_to_moderate)
        self.assertIsNone(result) # Expecting graceful None return

if __name__ == '__main__':
    # This allows running the tests directly from this file
    unittest.main()
