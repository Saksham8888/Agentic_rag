import logfire
from langchain_groq import ChatGroq

from app.config import settings

# Since Portkey inline configs are disabled on this account,
# we use LangChain's native fallback routing instead.

def get_langchain_llm(feature: str = "rag"):
    """
    Returns a ChatGroq instance with native LangChain fallbacks configured.
    Primary: openai/gpt-oss-120b
    Fallback: openai/gpt-oss-20b
    """
    primary_llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="openai/gpt-oss-120b",
        temperature=0,
        max_retries=2
    )
    
    fallback_key = settings.GROQ_FALLBACK_API_KEY or settings.GROQ_API_KEY
    fallback_llm = ChatGroq(
        api_key=fallback_key,
        model="openai/gpt-oss-20b",
        temperature=0,
        max_retries=2
    )
    
    # LangChain native fallback routing
    return primary_llm.with_fallbacks([fallback_llm])


# Dummy implementations to avoid breaking imports in responder.py
portkey_client = None

def extract_cache_status(response) -> str:
    return "MISS"