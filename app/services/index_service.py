from pathlib import Path

from llama_index.core import (
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.base.base_query_engine import BaseQueryEngine

from app.config import config
from app.services.llm import configure_models


def load_index() -> VectorStoreIndex:
    """Load the persistent vector index from storage."""

    configure_models()

    storage_path = Path(config.storage_dir)

    if not storage_path.exists():
        raise RuntimeError(
            "The vector index does not exist. "
            "Run `python -m app.ingest` first."
        )

    if not any(storage_path.iterdir()):
        raise RuntimeError(
            f"The storage directory is empty: {storage_path}"
        )

    storage_context = StorageContext.from_defaults(
        persist_dir=str(storage_path)
    )

    return load_index_from_storage(storage_context)


def load_query_engine() -> BaseQueryEngine:
    """Create a retrieval and response-synthesis query engine."""

    index = load_index()

    return index.as_query_engine(
        similarity_top_k=config.top_k,
        response_mode="compact",
    )