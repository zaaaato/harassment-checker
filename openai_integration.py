import openai
import logging # Import logging
from config import OPENAI_API_KEY # Import the API key from config

logger = logging.getLogger(__name__) # Get a logger instance

# Initialize the OpenAI client globally or manage appropriately.
# This ensures the client is initialized once when the module is imported.
if not OPENAI_API_KEY:
    # This case is technically handled by config.py raising an error,
    # but as a safeguard for this module's direct use or testing:
    logger.error("OPENAI_API_KEY is not configured. OpenAI client cannot be initialized.")
    client = None
else:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

def moderate_text(text_to_moderate: str):
    """
    Calls the OpenAI Moderation API to check if the given text violates OpenAI's usage policies.
    Uses the globally configured OpenAI client.

    Args:
        text_to_moderate: The text string to moderate.

    Returns:
        The moderation result object (response.results[0]) if successful,
        None if an error occurs, the API key is not configured, or client is not initialized.
    """
    if not client:
        logger.error("OpenAI client is not initialized (OPENAI_API_KEY likely missing). Cannot moderate text.")
        return None
    
    if not text_to_moderate: # Added a check for empty input
        logger.warning("Attempted to moderate empty or None text.")
        return None

    try:
        response = client.moderations.create(input=text_to_moderate)
        
        if response.results:
            return response.results[0]
        else:
            # Log the actual response if it's not what we expect
            logger.error(f"Unexpected OpenAI API response structure: {response}")
            return None
    except openai.APIConnectionError as e:
        logger.exception(f"OpenAI API request failed to connect: {e}")
        return None
    except openai.RateLimitError as e:
        logger.exception(f"OpenAI API request exceeded rate limit: {e}")
        return None
    except openai.APIStatusError as e:
        logger.exception(f"OpenAI API returned an API Error: {e.status_code} - {e.response}")
        return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred while calling OpenAI Moderation API: {e}")
        return None

if __name__ == "__main__":
    # The global OPENAI_API_KEY from config.py is used when this module loads.
    # Ensure .env is loaded by config.py if running this directly.
    # For direct testing, it's good practice to ensure config.py runs first or simulate its effect.
    
    # To ensure config.py's print statements (and .env loading) happen:
    try:
        # Importing config will ensure logging is set up if not already
        import config 
        logger.info("Config loaded via import for openai_integration.py __main__ test.")
    except ValueError as e: # Catch error from config.py if keys are missing
        logger.critical(f"Configuration error: {e}")
        # Optionally exit or skip tests if config is invalid
        exit(1)


    if not client:
        logger.warning("OpenAI client not initialized. Skipping moderation tests.")
    else:
        logger.info("\n--- Test 1: Benign text (using configured client) ---")
        test_text_1 = "This is a lovely sentence about kittens and sunshine."
        logger.info(f"Moderating: '{test_text_1}'")
        moderation_result_1 = moderate_text(test_text_1)
        if moderation_result_1:
            logger.info("Moderation Result (Benign Text):")
            logger.info(f"  Flagged: {moderation_result_1.flagged}")
            # Optional: print categories
            # for category, flagged in moderation_result_1.categories:
            #     if flagged:
            #         logger.info(f"    {category}: {moderation_result_1.category_scores.get(category)}")
        else:
            logger.error("Moderation call failed for benign text.")

        logger.info("\n--- Test 2: Potentially problematic text (using configured client) ---")
        test_text_2 = "I want to express strong anger and frustration."
        logger.info(f"Moderating: '{test_text_2}'")
        moderation_result_2 = moderate_text(test_text_2)
        if moderation_result_2:
            logger.info("Moderation Result (Problematic Text):")
            logger.info(f"  Flagged: {moderation_result_2.flagged}")
            if moderation_result_2.flagged:
                logger.info("  Categories flagged:")
                # The categories attribute is a Pydantic model, so iterate its fields
                for category_name, is_flagged in moderation_result_2.categories.__dict__.items():
                    if is_flagged:
                        score = moderation_result_2.category_scores.__dict__.get(category_name, 'N/A')
                        logger.info(f"    {category_name}: True (Score: {score})")
        else:
            logger.error("Moderation call failed for problematic text.")

        logger.info("\n--- Test 3: Example from OpenAI documentation (Self-harm) ---")
        test_text_3 = "I want to kill myself."
        logger.info(f"Moderating: '{test_text_3}'")
        moderation_result_3 = moderate_text(test_text_3)
        if moderation_result_3:
            logger.info("Moderation Result (Self-Harm Text):")
            logger.info(f"  Flagged: {moderation_result_3.flagged}")
            if moderation_result_3.flagged:
                logger.info("  Categories flagged:")
                for category_name, is_flagged in moderation_result_3.categories.__dict__.items():
                    if is_flagged:
                        score = moderation_result_3.category_scores.__dict__.get(category_name, 'N/A')
                        logger.info(f"    {category_name}: {is_flagged} (Score: {score})")
        else:
            logger.error("Moderation call failed for self-harm text.")
