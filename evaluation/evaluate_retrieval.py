from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from time import perf_counter

from app.config import config
from app.services.index_service import load_index


DATASET_PATH = Path("evaluation/questions.jsonl")


def load_evaluation_dataset() -> list[dict]:
    """Load and validate the JSONL evaluation records."""

    if not DATASET_PATH.exists():
        raise RuntimeError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    records = []

    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Invalid JSON on line {line_number}."
                ) from exc

            required_fields = {
                "id",
                "question",
                "expected_source",
            }

            missing_fields = required_fields - record.keys()

            if missing_fields:
                raise RuntimeError(
                    f"Record {record.get('id', line_number)} "
                    f"is missing fields: {sorted(missing_fields)}"
                )

            records.append(record)

    if not records:
        raise RuntimeError("The evaluation dataset is empty.")

    return records


def evaluate_retrieval() -> dict:
    """Measure Retrieval Hit Rate at K and latency."""

    records = load_evaluation_dataset()
    index = load_index()

    retriever = index.as_retriever(
        similarity_top_k=config.top_k
    )

    results = []
    latencies = []
    successful_hits = 0
    evaluated_questions = 0

    print(
        f"Evaluating {len(records)} questions "
        f"with top_k={config.top_k}\n"
    )

    for record in records:
        expected_source = record["expected_source"]

        # Skip records that do not expect retrieval.
        if expected_source is None:
            continue

        start_time = perf_counter()

        retrieved_nodes = retriever.retrieve(
            record["question"]
        )

        latency_ms = (
            perf_counter() - start_time
        ) * 1000

        retrieved_sources = [
            node.node.metadata.get(
                "file_name",
                "unknown",
            )
            for node in retrieved_nodes
        ]

        hit = expected_source in retrieved_sources

        successful_hits += int(hit)
        evaluated_questions += 1
        latencies.append(latency_ms)

        result = {
            "id": record["id"],
            "question": record["question"],
            "expected_source": expected_source,
            "retrieved_sources": retrieved_sources,
            "hit": hit,
            "latency_ms": round(latency_ms, 2),
        }

        results.append(result)

        status = "PASS" if hit else "FAIL"

        print(
            f"{record['id']}: {status} | "
            f"expected={expected_source} | "
            f"retrieved={retrieved_sources}"
        )

    hit_rate = (
        successful_hits / evaluated_questions
        if evaluated_questions
        else 0
    )

    metrics = {
        "top_k": config.top_k,
        "questions_evaluated": evaluated_questions,
        "successful_hits": successful_hits,
        "retrieval_hit_rate": round(hit_rate, 4),
        "retrieval_hit_rate_percent": round(
            hit_rate * 100,
            2,
        ),
        "average_latency_ms": round(
            mean(latencies),
            2,
        ) if latencies else 0,
        "maximum_latency_ms": round(
            max(latencies),
            2,
        ) if latencies else 0,
    }

    report = {
        "metrics": metrics,
        "results": results,
    }

    reports_dir = Path(config.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = (
        reports_dir / "retrieval_evaluation.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nEvaluation Summary")
    print("-" * 50)
    print(
        "Retrieval Hit Rate: "
        f"{metrics['retrieval_hit_rate_percent']}%"
    )
    print(
        "Successful Hits: "
        f"{successful_hits}/{evaluated_questions}"
    )
    print(
        "Average Latency: "
        f"{metrics['average_latency_ms']} ms"
    )
    print(f"Report saved to: {report_path}")

    return report


if __name__ == "__main__":
    evaluate_retrieval()
