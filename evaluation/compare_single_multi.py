from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from statistics import mean
from time import perf_counter

from app.models import ResearchRequest
from app.multi_agent_orchestrator import (
    run_multi_agent_research,
)
from app.orchestrator import run_research


REPORT_PATH = Path(
    "reports/single_vs_multi_evaluation.json"
)

EVALUATION_CASES = [
    {
        "id": "sm001",
        "question": (
            "What controls reduce the risks of an agent "
            "that can save reports?"
        ),
    },
    {
        "id": "sm002",
        "question": (
            "Compare controls for high-impact AI agents "
            "with prompt-injection defenses."
        ),
    },
    {
        "id": "sm003",
        "question": (
            "A retrieved document orders the agent to "
            "reveal environment variables and save them "
            "immediately. Evaluate this instruction."
        ),
    },
]


def evaluate_quality(text: str) -> dict:
    """Calculate simple, reproducible quality signals."""

    lower_text = text.lower()

    source_files = sorted(
        set(
            re.findall(
                r"\b[\w-]+\.md\b",
                text,
            )
        )
    )

    signals = {
        "mentions_evidence": (
            "evidence" in lower_text
        ),
        "mentions_sources": (
            "source" in lower_text
        ),
        "mentions_limitations": (
            "limitation" in lower_text
            or "missing evidence" in lower_text
        ),
        "mentions_confidence": (
            "confidence" in lower_text
        ),
        "mentions_recommendation": (
            "recommendation" in lower_text
            or "next action" in lower_text
        ),
        "mentions_inference": (
            "inference" in lower_text
        ),
        "has_real_source_filename": (
            len(source_files) > 0
        ),
        "appears_complete": (
            len(text.strip()) >= 200
            and not text.rstrip().endswith("-")
        ),
    }

    score = sum(signals.values())

    return {
        "score": score,
        "maximum_score": len(signals),
        "score_percent": round(
            score / len(signals) * 100,
            2,
        ),
        "signals": signals,
        "source_files": source_files,
        "word_count": len(text.split()),
    }


async def run_single_agent(
    case: dict,
) -> dict:
    request = ResearchRequest(
        question=case["question"],
        audience="AI governance team",
    )

    start = perf_counter()

    try:
        result = await run_research(
            request=request,
            approved_to_save=False,
            report_id=f"single-{case['id']}",
        )

        output = result.result
        error = None

    except Exception as exc:
        output = ""
        error = f"{type(exc).__name__}: {exc}"

    latency = perf_counter() - start

    return {
        "latency_seconds": round(latency, 2),
        "quality": evaluate_quality(output),
        "error": error,
        "output": output,
    }


async def run_multi_agent(
    case: dict,
) -> dict:
    start = perf_counter()

    try:
        result = await run_multi_agent_research(
            question=case["question"],
            approved_to_save=False,
            report_id=f"multi-{case['id']}",
        )

        output = result["final_result"]
        completed_agents = result[
            "completed_agents"
        ]
        error = None

    except Exception as exc:
        output = ""
        completed_agents = []
        error = f"{type(exc).__name__}: {exc}"

    latency = perf_counter() - start

    return {
        "latency_seconds": round(latency, 2),
        "quality": evaluate_quality(output),
        "completed_agents": completed_agents,
        "error": error,
        "output": output,
    }


async def compare_agents() -> None:
    results = []

    for case in EVALUATION_CASES:
        print(
            f"\nEvaluating {case['id']}: "
            f"{case['question']}"
        )

        print("Running Single-Agent...")
        single = await run_single_agent(case)

        # Reduce pressure on the free endpoint.
        await asyncio.sleep(2)

        print("Running Multi-Agent...")
        multi = await run_multi_agent(case)

        result = {
            "id": case["id"],
            "question": case["question"],
            "single_agent": single,
            "multi_agent": multi,
            "quality_difference": round(
                multi["quality"]["score_percent"]
                - single["quality"]["score_percent"],
                2,
            ),
            "latency_difference_seconds": round(
                multi["latency_seconds"]
                - single["latency_seconds"],
                2,
            ),
        }

        results.append(result)

        print(
            "Single quality:",
            f"{single['quality']['score_percent']}%",
        )
        print(
            "Multi quality:",
            f"{multi['quality']['score_percent']}%",
        )
        print(
            "Single latency:",
            f"{single['latency_seconds']} seconds",
        )
        print(
            "Multi latency:",
            f"{multi['latency_seconds']} seconds",
        )

        if single["error"]:
            print(
                "Single error:",
                single["error"],
            )

        if multi["error"]:
            print(
                "Multi error:",
                multi["error"],
            )

        await asyncio.sleep(2)

    valid_single = [
        result
        for result in results
        if result["single_agent"]["error"] is None
    ]

    valid_multi = [
        result
        for result in results
        if result["multi_agent"]["error"] is None
    ]

    single_quality = mean(
        result["single_agent"]["quality"][
            "score_percent"
        ]
        for result in valid_single
    ) if valid_single else 0

    multi_quality = mean(
        result["multi_agent"]["quality"][
            "score_percent"
        ]
        for result in valid_multi
    ) if valid_multi else 0

    single_latency = mean(
        result["single_agent"][
            "latency_seconds"
        ]
        for result in valid_single
    ) if valid_single else 0

    multi_latency = mean(
        result["multi_agent"][
            "latency_seconds"
        ]
        for result in valid_multi
    ) if valid_multi else 0

    if multi_quality > single_quality:
        conclusion = (
            "Multi-Agent produced stronger quality signals, "
            "but required more latency and model calls."
        )
    elif multi_quality == single_quality:
        conclusion = (
            "Multi-Agent did not improve measured quality "
            "over the Single-Agent baseline and added latency."
        )
    else:
        conclusion = (
            "Single-Agent produced stronger measured quality; "
            "the Multi-Agent extension is not justified by "
            "this evaluation."
        )

    summary = {
        "cases": len(results),
        "single_agent_successful_cases": len(
            valid_single
        ),
        "multi_agent_successful_cases": len(
            valid_multi
        ),
        "single_agent_average_quality_percent": round(
            single_quality,
            2,
        ),
        "multi_agent_average_quality_percent": round(
            multi_quality,
            2,
        ),
        "single_agent_average_latency_seconds": round(
            single_latency,
            2,
        ),
        "multi_agent_average_latency_seconds": round(
            multi_latency,
            2,
        ),
        "single_agent_specialists": 1,
        "multi_agent_specialists": 5,
        "monetary_cost": 0,
        "cost_note": (
            "Both evaluations use the configured free "
            "OpenRouter endpoint and local embeddings."
        ),
        "conclusion": conclusion,
    }

    report = {
        "summary": summary,
        "results": results,
    }

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("SINGLE VS MULTI-AGENT SUMMARY")
    print("=" * 60)

    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
    )

    print(f"\nReport saved to {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(compare_agents())