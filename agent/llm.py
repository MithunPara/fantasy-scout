from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from agent.settings import settings

def get_llm() -> BaseChatModel:
    return init_chat_model(
        settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        api_key=settings.groq_api_key.get_secret_value(),
        max_retries=settings.LLM_MAX_RETRIES,
        timeout=settings.LLM_TIMEOUT
    )