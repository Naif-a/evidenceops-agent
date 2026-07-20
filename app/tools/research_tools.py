from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from llama_index.core.tools import FunctionTool, QueryEngineTool

from app.config import config
from app.services.index_service import load_query_engine


def sanitize_filename(title: str) -> str:
    """Convert a report title into a safe filename."""

    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        title.strip().lower(),
    )

    safe_name = safe_name.strip("_")[:60]

    if not safe_name:
        raise ValueError("The report title cannot be empty.")

    return safe_name


def save_report(
    title: str,
    content: str,
    report_id: str,
) -> str:
    """Save an approved report with deterministic auditing."""

    if not report_id.strip():
        raise ValueError("A report ID is required.")

    if not title.strip():
        raise ValueError("A report title is required.")

    if not content.strip():
        raise ValueError("Report content cannot be empty.")

    reports_dir = Path(config.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(title)
    report_path = (reports_dir / f"{safe_name}.md").resolve()

    if report_path.parent != reports_dir:
        raise ValueError("Invalid report path.")

    record_audit_event(
        action="report_save_started",
        detail=f"Preparing to save {report_path.name}",
        report_id=report_id,
    )

    try:
        report_path.write_text(
            content,
            encoding="utf-8",
        )
    except Exception as exc:
        record_audit_event(
            action="report_save_failed",
            detail=f"{type(exc).__name__}: save failed",
            report_id=report_id,
        )
        raise

    record_audit_event(
        action="report_save_completed",
        detail=f"Saved {report_path.name}",
        report_id=report_id,
    )

    return f"Report saved to {report_path}"


def record_audit_event(
    action: str,
    detail: str,
    report_id: str = "unassigned",
) -> str:
    """Append an event to the JSONL audit log."""

    if not action.strip():
        raise ValueError("Audit action cannot be empty.")

    reports_dir = Path(config.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    log_path = reports_dir / "audit_log.jsonl"

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "report_id": report_id,
        "action": action.strip(),
        "detail": detail.strip(),
    }

    with log_path.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(event, ensure_ascii=False) + "\n"
        )

    return "Audit event recorded."


def compare_sources(topic_a: str, topic_b: str) -> str:
    """Retrieve evidence for two topics and compare their sources."""

    if not topic_a.strip() or not topic_b.strip():
        raise ValueError("Both comparison topics are required.")

    query_engine = load_query_engine()

    response_a = query_engine.query(topic_a)
    response_b = query_engine.query(topic_b)

    sources_a = {
        item.node.metadata.get("file_name", "unknown")
        for item in response_a.source_nodes
    }

    sources_b = {
        item.node.metadata.get("file_name", "unknown")
        for item in response_b.source_nodes
    }

    comparison = {
        "topic_a": {
            "topic": topic_a,
            "finding": str(response_a),
            "sources": sorted(sources_a),
        },
        "topic_b": {
            "topic": topic_b,
            "finding": str(response_b),
            "sources": sorted(sources_b),
        },
        "overlapping_sources": sorted(sources_a & sources_b),
        "sources_only_for_topic_a": sorted(sources_a - sources_b),
        "sources_only_for_topic_b": sorted(sources_b - sources_a),
        "evidence_limitations": (
            "The comparison is limited to documents currently "
            "available in the indexed knowledge base."
        ),
    }

    return json.dumps(
        comparison,
        ensure_ascii=False,
        indent=2,
    )


def build_tools(
    approved_to_save: bool = False,
    report_id: str | None = None,
) -> list:
    """Build request-specific tools and permissions."""

    query_engine = load_query_engine()

    knowledge_tool = QueryEngineTool.from_defaults(
        query_engine=query_engine,
        name="knowledge_base_search",
        description=(
            "Search the indexed EvidenceOps knowledge base. "
            "Use this before making factual claims and report "
            "the supporting source filenames."
        ),
    )

    comparison_tool = FunctionTool.from_defaults(
        fn=compare_sources,
        name="compare_sources",
        description=(
            "Compare evidence for two research topics. It performs "
            "two knowledge-base queries and returns findings, shared "
            "sources, differences, and evidence limitations. It does "
            "not save files."
        ),
    )

    audit_tool = FunctionTool.from_defaults(
        fn=record_audit_event,
        name="record_audit_event",
        description=(
            "Record a concise audit event for an important research "
            "action. Report saving is audited automatically."
        ),
    )

    tools = [
        knowledge_tool,
        comparison_tool,
        audit_tool,
    ]

    if approved_to_save:
        if not report_id:
            raise ValueError(
                "An approved agent requires a report ID."
            )

        # Bind the report ID in deterministic application code.
        # The model cannot change or omit it.
        def save_approved_report(
            title: str,
            content: str,
        ) -> str:
            """Save the approved report for this request."""

            return save_report(
                title=title,
                content=content,
                report_id=report_id,
            )

        save_tool = FunctionTool.from_defaults(
            fn=save_approved_report,
            name="save_report",
            description=(
                "Save the final human-approved Markdown report. "
                "This tool is available only for the currently "
                "approved request, and saving is audited automatically."
            ),
        )

        tools.append(save_tool)

    return tools