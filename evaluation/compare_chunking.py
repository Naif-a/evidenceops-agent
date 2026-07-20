from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from time import perf_counter

from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SentenceSplitter

from app.config import config
from app.services.llm import configure_models


CHUNKING_VARIANTS = [
    {"chunk_size": 350, "chunk_overlap": 50},
    {"chunk_size": 700, "chunk_overlap": 100},
    {"chunk_size": 1200, "chunk_overlap": 150},
]


def load_questions() -> list[dict]:
    dataset_path = Path("evaluation/questions.jsonl")

    with dataset_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return [
            json.loads(line)
            for line in file
            if line.strip()
        ]


def load_documents():
    documents = SimpleDirectoryReader(
        input_dir=config.data_dir,
        recursive=True,
    ).load_data()

    if not documents:
        raise RuntimeError("No documents were loaded.")

    for document in documents:
        file_name = document.metadata.get(
            "file_name",
            "unknown",
        )

        document.metadata["source_name"] = file_name
        document.metadata["collection"] = (
            "evidenceops_knowledge"
        )
        document.metadata["trust_level"] = "untrusted"
        document.metadata["instruction_authority"] = "none"

    return documents


def evaluate_variant(
    chunk_size: int,
    chunk_overlap: int,
    questions: list[dict],
) -> dict:
    documents = load_documents()

    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    nodes = splitter.get_nodes_from_documents(
        documents
    )

    index = VectorStoreIndex(nodes)

    variant_storage = Path(
        f"storage/chunk_{chunk_size}_{chunk_overlap}"
    )

    variant_storage.mkdir(
        parents=True,
        exist_ok=True,
    )

    index.storage_context.persist(
        persist_dir=str(variant_storage)
    )

    retriever = index.as_retriever(
        similarity_top_k=config.top_k
    )

    hits = 0
    latencies = []
    details = []

    for record in questions:
        expected_source = record.get("expected_source")

        if expected_source is None:
            continue

        start = perf_counter()

        retrieved_nodes = retriever.retrieve(
            record["question"]
        )

        latency_ms = (
            perf_counter() - start
        ) * 1000

        sources = [
            item.node.metadata.get(
                "file_name",
                "unknown",
            )
            for item in retrieved_nodes
        ]

        hit = expected_source in sources

        hits += int(hit)
        latencies.append(latency_ms)

        details.append(
            {
                "id": record["id"],
                "expected_source": expected_source,
                "retrieved_sources": sources,
                "hit": hit,
            }
        )

    total = len(details)
    hit_rate = hits / total if total else 0

    return {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "document_count": len(documents),
        "node_count": len(nodes),
        "questions_evaluated": total,
        "successful_hits": hits,
        "hit_rate_percent": round(
            hit_rate * 100,
            2,
        ),
        "average_latency_ms": round(
            mean(latencies),
            2,
        ) if latencies else 0,
        "storage_directory": str(variant_storage),
        "details": details,
    }


def compare_chunking() -> None:
    configure_models()

    questions = load_questions()
    results = []

    for variant in CHUNKING_VARIANTS:
        print(
            "\nTesting "
            f"chunk_size={variant['chunk_size']}, "
            f"chunk_overlap={variant['chunk_overlap']}"
        )

        result = evaluate_variant(
            chunk_size=variant["chunk_size"],
            chunk_overlap=variant["chunk_overlap"],
            questions=questions,
        )

        results.append(result)

        print(f"Nodes: {result['node_count']}")
        print(
            "Hit Rate: "
            f"{result['hit_rate_percent']}%"
        )
        print(
            "Average Latency: "
            f"{result['average_latency_ms']} ms"
        )

    best_variant = max(
        results,
        key=lambda item: (
            item["hit_rate_percent"],
            -item["average_latency_ms"],
        ),
    )

    report = {
        "variants": results,
        "recommended_variant": {
            "chunk_size": best_variant["chunk_size"],
            "chunk_overlap": best_variant[
                "chunk_overlap"
            ],
            "hit_rate_percent": best_variant[
                "hit_rate_percent"
            ],
            "reason": (
                "Highest retrieval hit rate, with latency "
                "used as the tie-breaker."
            ),
        },
    }

    reports_dir = Path(config.reports_dir)
    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        reports_dir / "chunking_comparison.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nRecommended Configuration")
    print("-" * 40)
    print(
        "Chunk size:",
        best_variant["chunk_size"],
    )
    print(
        "Chunk overlap:",
        best_variant["chunk_overlap"],
    )
    print(
        "Hit rate:",
        f"{best_variant['hit_rate_percent']}%",
    )
    print("Report saved to:", report_path)


if __name__ == "__main__":
    compare_chunking()
