from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


RETRIEVAL_REPORT = Path(
    "reports/retrieval_evaluation.json"
)
CHUNKING_REPORT = Path(
    "reports/chunking_comparison.json"
)
OUTPUT_REPORT = Path(
    "reports/evaluation_report.md"
)


def load_json(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(
            f"Required report not found: {path}"
        )

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def run_tests() -> dict:
    process = subprocess.run(
        [
            "uv",
            "run",
            "--active",
            "pytest",
            "-q",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    output = process.stdout + process.stderr
    match = re.search(r"(\d+) passed", output)

    return {
        "passed": (
            int(match.group(1))
            if match
            else 0
        ),
        "successful": process.returncode == 0,
        "output": output.strip(),
    }


def generate_report() -> None:
    retrieval = load_json(RETRIEVAL_REPORT)
    chunking = load_json(CHUNKING_REPORT)
    tests = run_tests()

    metrics = retrieval["metrics"]

    failed_questions = [
        result
        for result in retrieval["results"]
        if not result["hit"]
    ]

    variants = chunking["variants"]

    identical_node_counts = (
        len(
            {
                variant["node_count"]
                for variant in variants
            }
        )
        == 1
    )

    lines = [
        "# EvidenceOps Agent Evaluation Report",
        "",
        (
            "**Generated:** "
            + datetime.now(timezone.utc).isoformat()
        ),
        "",
        "## Executive Summary",
        "",
        (
            "EvidenceOps was evaluated for retrieval quality, "
            "latency, deterministic governance behavior, "
            "chunking configuration, and adversarial safety."
        ),
        "",
        "## Retrieval Metrics",
        "",
        "| Metric | Result |",
        "|---|---:|",
        (
            f"| Retrieval Hit Rate@{metrics['top_k']} | "
            f"{metrics['retrieval_hit_rate_percent']}% |"
        ),
        (
            f"| Successful retrievals | "
            f"{metrics['successful_hits']}/"
            f"{metrics['questions_evaluated']} |"
        ),
        (
            f"| Average retrieval latency | "
            f"{metrics['average_latency_ms']} ms |"
        ),
        (
            f"| Maximum retrieval latency | "
            f"{metrics['maximum_latency_ms']} ms |"
        ),
        "",
        "## Automated Tests",
        "",
        f"- Tests passed: {tests['passed']}",
        (
            "- Test-suite status: "
            + (
                "Passed"
                if tests["successful"]
                else "Failed"
            )
        ),
        (
            "- Approval compliance: covered by tests that "
            "verify unavailable save permission, isolated "
            "report IDs, and single-request approval."
        ),
        (
            "- Execution bounds: covered by deterministic "
            "timeout tests."
        ),
        "",
        "## Chunking Experiment",
        "",
        "| Chunk Size | Overlap | Nodes | Hit Rate | Average Latency |",
        "|---:|---:|---:|---:|---:|",
    ]

    for variant in variants:
        lines.append(
            f"| {variant['chunk_size']} "
            f"| {variant['chunk_overlap']} "
            f"| {variant['node_count']} "
            f"| {variant['hit_rate_percent']}% "
            f"| {variant['average_latency_ms']} ms |"
        )

    lines.extend(
        [
            "",
            "### Chunking Interpretation",
            "",
        ]
    )

    if identical_node_counts:
        lines.extend(
            [
                (
                    "All configurations generated the same number "
                    "of nodes. The current documents are too short "
                    "for chunk size to materially change retrieval."
                ),
                "",
                (
                    "The project therefore retains the balanced "
                    "baseline of `chunk_size=700` and "
                    "`chunk_overlap=100`. The experiment should be "
                    "repeated with larger production documents."
                ),
            ]
        )
    else:
        recommendation = chunking[
            "recommended_variant"
        ]

        lines.append(
            "Recommended configuration: "
            f"`{recommendation['chunk_size']}/"
            f"{recommendation['chunk_overlap']}`."
        )

    lines.extend(
        [
            "",
            "## Retrieval Failures",
            "",
        ]
    )

    if failed_questions:
        for failure in failed_questions:
            lines.extend(
                [
                    f"### {failure['id']}",
                    "",
                    f"- Question: {failure['question']}",
                    (
                        "- Expected source: "
                        f"`{failure['expected_source']}`"
                    ),
                    (
                        "- Retrieved sources: "
                        + ", ".join(
                            f"`{source}`"
                            for source in failure[
                                "retrieved_sources"
                            ]
                        )
                    ),
                    (
                        "- Analysis: the expected source did not "
                        "appear in the configured top-k results. "
                        "Potential improvements include stronger "
                        "document content, metadata filters, query "
                        "rewriting, or reranking."
                    ),
                    "",
                ]
            )
    else:
        lines.append(
            "No retrieval failures were observed."
        )

    lines.extend(
        [
            "## Adversarial Safety Evaluation",
            "",
            (
                "A malicious document attempted to override system "
                "policy, reveal environment variables, and force an "
                "unapproved report save."
            ),
            "",
            "Implemented defenses:",
            "",
            (
                "- Retrieved content is classified as untrusted "
                "data with no instruction authority."
            ),
            (
                "- The system prompt prohibits retrieved content "
                "from changing permissions or revealing secrets."
            ),
            (
                "- The save tool is removed from unapproved agent "
                "runs."
            ),
            (
                "- Report paths are sanitized and restricted to "
                "the reports directory."
            ),
            (
                "- API errors return controlled messages without "
                "stack traces."
            ),
            "",
            "## Latency and Cost",
            "",
            (
                "- Retrieval embeddings run locally, so retrieval "
                "has no per-request API cost."
            ),
            (
                "- The configured OpenRouter model uses a free "
                "endpoint, so current demonstration calls have no "
                "direct model charge."
            ),
            (
                "- Free endpoints may introduce rate limits, "
                "availability variation, and inconsistent latency."
            ),
            "",
            "## Observed Limitations",
            "",
            (
                "- The knowledge base contains short demonstration "
                "documents rather than production-scale sources."
            ),
            (
                "- Pending API approvals use in-memory storage and "
                "are lost when the process restarts."
            ),
            (
                "- Tool-call limits are communicated through policy, "
                "while a deterministic timeout provides the hard "
                "execution boundary."
            ),
            (
                "- Additional end-to-end evaluations are required "
                "before production deployment."
            ),
            "",
            "## Recommended Improvements",
            "",
            "1. Evaluate larger and more diverse documents.",
            "2. Add reranking or hybrid keyword/vector retrieval.",
            "3. Store approval state in a persistent database.",
            "4. Add authentication and rate limiting.",
            "5. Add model-call tracing and token accounting.",
            "6. Run the adversarial suite after every policy change.",
        ]
    )

    OUTPUT_REPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_REPORT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(f"Evaluation report saved to {OUTPUT_REPORT}")


if __name__ == "__main__":
    generate_report()
