from pathlib import Path
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from app.config import config
from app.services.llm import configure_models


def build_index() -> None:
    """Load documents, create chunks, and persist the vector index."""

    configure_models()

    data_path = Path(config.data_dir)
    storage_path = Path(config.storage_dir)

    if not data_path.exists():
        raise RuntimeError(
            f"Data directory does not exist: {data_path}"
        )

    files = [path for path in data_path.rglob("*") if path.is_file()]

    if not files:
        raise RuntimeError(
            f"No documents found in the data directory: {data_path}"
        )

    documents = SimpleDirectoryReader(
        input_dir=str(data_path),
        recursive=True,
    ).load_data()

    if not documents:
        raise RuntimeError("No supported documents could be loaded.")

    # Add useful metadata to every document.
    for document in documents:
        file_name = document.metadata.get("file_name", "unknown")
        file_path = Path(file_name)

        document.metadata["source_type"] = (
            file_path.suffix.lower() or "unknown"
        )
        document.metadata["collection"] = "evidenceops_knowledge"
        document.metadata["source_name"] = file_path.name

        document.metadata["trust_level"] = "untrusted"
        document.metadata["instruction_authority"] = "none"

    if config.chunk_overlap >= config.chunk_size:
        raise ValueError(
            "CHUNK_OVERLAP must be smaller than CHUNK_SIZE."
        )

    splitter = SentenceSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )

    nodes = splitter.get_nodes_from_documents(
        documents,
        show_progress=True,
    )

    if not nodes:
        raise RuntimeError("Document chunking produced no nodes.")

    index = VectorStoreIndex(
        nodes,
        show_progress=True,
    )

    storage_path.mkdir(parents=True, exist_ok=True)

    index.storage_context.persist(
        persist_dir=str(storage_path)
    )

    print(f"Loaded documents: {len(documents)}")
    print(f"Created chunks: {len(nodes)}")
    print(f"Index saved to: {storage_path.resolve()}")


if __name__ == "__main__":
    build_index()