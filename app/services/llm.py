import logging

from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike

from app.config import config


logger = logging.getLogger(__name__)


def configure_models() -> None:
    """Configure OpenRouter LLM and local embedding model."""

    if config.model_provider != "openrouter":
        raise ValueError(
            f"Unsupported model provider: {config.model_provider}"
        )

    api_key = config.openrouter_api_key.get_secret_value()

    if not api_key.strip():
        raise ValueError("OPENROUTER_API_KEY is missing or empty.")

    Settings.llm = OpenAILike(
        model=config.llm_model,
        api_base=config.openrouter_api_base,
        api_key=api_key,
        temperature=0.1,
        context_window=config.llm_context_window,
        max_tokens=config.llm_max_tokens,
        is_chat_model=True,
        is_function_calling_model=True,
    )

    Settings.embed_model = HuggingFaceEmbedding(
        model_name=config.embedding_model,
    )

    logger.info(
        "Models configured: provider=%s, llm=%s, embedding=%s",
        config.model_provider,
        config.llm_model,
        config.embedding_model,
    )