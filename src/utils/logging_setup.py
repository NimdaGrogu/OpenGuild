from langchain_core.callbacks import BaseCallbackHandler
import logging
logger = logging.getLogger("CallbackHandler Logger")
logger.setLevel(logging.DEBUG)

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