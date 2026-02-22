from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Union


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ''
    openai_model: str = 'gpt-4o-mini'
    openai_embedding_model: str = 'text-embedding-3-small'

    # Local model (Ollama)
    use_local_models: bool = False
    local_model_name: str = 'llama3.2'
    ollama_base_url: str = 'http://ollama:11434'

    # Qdrant
    qdrant_host: str = 'qdrant'
    qdrant_port: int = 6333
    qdrant_collection: str = 'audit_documents'

    # Redis
    redis_url: str = 'redis://redis:6379'

    # Security
    guardrails_url: str = 'http://guardrails:8080'
    use_guardrails: bool = True

    # Services
    evaluation_service_url: str = 'http://evaluation:8001'
    cost_tracking_enabled: bool = True

    class Config:
        env_file = '.env'
        extra = 'ignore'


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def get_llm(temperature: float = 0):
    """
    Model factory: returns OpenAI or Ollama LLM based on USE_LOCAL_MODELS.
    All agents and tools use this function — switching the flag switches everything.
    """
    settings = get_settings()
    if settings.use_local_models:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.local_model_name,
            temperature=temperature,
            base_url=settings.ollama_base_url,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temperature,
            openai_api_key=settings.openai_api_key,
        )


def get_embeddings():
    """Embeddings: always use OpenAI (Ollama embeddings are lower quality)."""
    settings = get_settings()
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        openai_api_key=settings.openai_api_key,
    )
