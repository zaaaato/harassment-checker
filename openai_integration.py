"""
Provides functionality to interact with the OpenAI Moderation API.

This module handles the initialization of the OpenAI client and offers
a function to send text to the moderation endpoint for analysis.
Error handling for API calls is included.
"""
import openai
import logging
from config import OPENAI_API_KEY # Import the API key from config

logger = logging.getLogger(__name__)

# Initialize the OpenAI client.
# This client object will be used for all OpenAI API interactions within this module.
# It's initialized when the module is first imported, using the API key from config.py.
if not OPENAI_API_KEY:
    # This condition is primarily a safeguard. config.py should raise a ValueError
    # if OPENAI_API_KEY is missing, which would typically prevent this module from loading.
    logger.error("CRITICAL: OPENAI_API_KEY is not configured. OpenAI client cannot be initialized.")
    client = None
else:
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully.")
    except Exception as e:
        logger.exception("Failed to initialize OpenAI client during import.")
        client = None


def moderate_text(text_to_moderate: str):
    """
    Sends the provided text to the OpenAI Moderation API for content analysis.

    Args:
        text_to_moderate (str): The text string to be moderated.

    Returns:
        openai.types.moderation.Moderation (or similar object based on SDK version): 
            The first result object from the OpenAI Moderation API response, 
            containing flags and category scores, if the call is successful.
        None: 
            If the OpenAI client is not initialized, if the input text is empty or None,
            or if any error occurs during the API call (e.g., connection issues,
            API errors, unexpected response structure).
    """
    if not client:
        logger.error("OpenAI client is not initialized. Cannot moderate text.")
        return None
    
    if not text_to_moderate: # Check for empty or None input text
        logger.warning("Attempted to moderate empty or None text. Skipping API call.")
        return None

    try:
        # Call the OpenAI Moderation API endpoint.
        response = client.moderations.create(input=text_to_moderate)
        
        # The response object typically contains a 'results' list.
        # We are interested in the first item of this list.
        if response.results and len(response.results) > 0:
            return response.results[0] # Return the main moderation result object
        else:
            # Log an error if the response structure is not as expected.
            logger.error(f"Unexpected OpenAI API response structure: No results found. Response: {response}")
            return None
    # Handle specific OpenAI API errors as well as general exceptions.
    except openai.APIConnectionError as e:
        logger.exception(f"OpenAI API request failed to connect: {e}")
        return None
    except openai.RateLimitError as e:
        logger.exception(f"OpenAI API request exceeded rate limit: {e}")
        return None
    except openai.APIStatusError as e: # Covers HTTP status errors (4xx, 5xx)
        logger.exception(f"OpenAI API returned an error status: {e.status_code} - {e.response}")
        return None
    except Exception as e: # Catch any other unexpected errors
        logger.exception(f"An unexpected error occurred while calling OpenAI Moderation API: {e}")
        return None

# This block allows for basic testing of the moderate_text function when
# this script is executed directly (e.g., `python openai_integration.py`).
if __name__ == "__main__":
    # This ensures that config.py (which sets up logging and loads .env) is processed.
    # It's important for standalone testing of this module.
    try:
        import config # Ensures config is loaded, .env vars are available, and logging is set up.
        logger.info("Config loaded successfully for openai_integration.py direct execution.")
    except ValueError as e: 
        # This occurs if config.py raises ValueError due to missing essential API keys.
        logger.critical(f"Failed to load config due to missing environment variables: {e}")
        logger.warning("Cannot run openai_integration.py tests without essential API keys (OPENAI_API_KEY, etc.).")
        # Exit if config fails, as client would not be initialized.
        if not client: # Check if client initialization itself failed earlier due to missing key
             exit(1)


    if not client:
        logger.warning("OpenAI client not initialized (OPENAI_API_KEY likely missing or failed init). Skipping moderation tests in __main__.")
    else:
        # Example usage for testing
        logger.info("--- OpenAI Integration Direct Test: Benign text ---")
        test_text_1 = "This is a lovely sentence about kittens and sunshine."
        logger.info(f"Moderating: '{test_text_1}'")
        moderation_result_1 = moderate_text(test_text_1)
        if moderation_result_1:
            logger.info(f"Moderation Result (Benign Text): Flagged={moderation_result_1.flagged}")
            # You can iterate through moderation_result_1.categories.__dict__.items() to see all boolean flags
            # And moderation_result_1.category_scores.__dict__.items() for scores
        else:
            logger.error("Moderation call failed for benign text.")

        logger.info("\n--- OpenAI Integration Direct Test: Potentially problematic text ---")
        # Note: This text will be sent to OpenAI if the script is run directly.
        test_text_2 = "I want to express strong anger and frustration about the situation."
        logger.info(f"Moderating: '{test_text_2}'")
        moderation_result_2 = moderate_text(test_text_2)
        if moderation_result_2:
            logger.info(f"Moderation Result (Problematic Text): Flagged={moderation_result_2.flagged}")
            if moderation_result_2.flagged:
                logger.info("  Categories flagged:")
                for category_name, is_flagged in moderation_result_2.categories.__dict__.items():
                    if is_flagged:
                        score = moderation_result_2.category_scores.__dict__.get(category_name, 'N/A')
                        logger.info(f"    {category_name}: True (Score: {score})")
        else:
            logger.error("Moderation call failed for problematic text.")

        logger.info("\n--- OpenAI Integration Direct Test: Example of self-harm text ---")
        # This is an example from OpenAI documentation and will be flagged.
        test_text_3 = "I want to kill myself."
        logger.info(f"Moderating: '{test_text_3}'")
        moderation_result_3 = moderate_text(test_text_3)
        if moderation_result_3:
            logger.info(f"Moderation Result (Self-Harm Text): Flagged={moderation_result_3.flagged}")
            if moderation_result_3.flagged:
                logger.info("  Categories flagged:")
                for category_name, is_flagged in moderation_result_3.categories.__dict__.items():
                    if is_flagged:
                        score = moderation_result_3.category_scores.__dict__.get(category_name, 'N/A')
                        logger.info(f"    {category_name}: {is_flagged} (Score: {score})")
        else:
            logger.error("Moderation call failed for self-harm text.")
