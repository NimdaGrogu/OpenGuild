from langchain_core.callbacks import BaseCallbackHandler
import re
import logging
logger = logging.getLogger("rag_debugger")

def extract_match_score(response_text):
    # Search for a number between 0 and 100
    match = re.search(r'\b(100|[1-9]?[0-9])\b', response_text)
    if match:
        return int(match.group(0))
    return 0

class DebugCallbackHandler(BaseCallbackHandler):

    def on_llm_start(self, serialized, prompts, **kwargs):
        """Run when LLM starts running. This gives us the FINAL prompt sent to the LLM."""
        logger.info("============== 📤 PROMPT SENT TO MODEL ==============")
        # prompts[0] is the final string with context and question injected
        logger.info(prompts[0])
        logger.info("=====================================================")

    def on_llm_end(self, response, **kwargs):
        """Run when LLM ends running."""
        logger.info("============== 📥 RESPONSE FROM MODEL ===============")
        # Access the actual text generated
        logger.info(response.generations[0][0].text)
        logger.info("=====================================================")