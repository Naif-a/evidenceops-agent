import json
from pathlib import Path

import pytest

from app.config import config
from app.tools.research_tools import (
    record_audit_event,
    sanitize_filename,
    save_report,
)


def test_sanitize_filename() -> None:
    result = sanitize_filename("AI Governance Report")

    assert result == "ai_governance_report"


def test_sanitize_filename_removes_unsafe_characters() -> None:
    result = sanitize_filename("../../Unsafe Report!")

    assert "/" not in result
    assert "." not in result
    assert result == "unsafe_report"


def test_sanitize_filename_rejects_empty_title() -> None:
    with pytest.raises(ValueError):
        sanitize_filename("!!!")


def test_save_report_creates_markdown_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports_dir = tmp_path / "reports"

    monkeypatch.setattr(
        config,
        "reports_dir",
        str(reports_dir),
    )

    message = save_report(
        title="Test Report",
        content="# Test result",
        report_id="test-report-001",
    )

    report_path = reports_dir / "test_report.md"

    assert report_path.exists()
    assert report_path.read_text(
        encoding="utf-8"
    ) == "# Test result"
    assert "saved" in message.lower()


def test_save_report_rejects_empty_content() -> None:
    with pytest.raises(ValueError):
        save_report(
            title="Empty Report",
            content="   ",
            report_id="test-report-002",
    )


def test_record_audit_event_creates_jsonl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports_dir = tmp_path / "reports"

    monkeypatch.setattr(
        config,
        "reports_dir",
        str(reports_dir),
    )

    record_audit_event(
        action="test_action",
        detail="A test event occurred.",
        report_id="report-123",
    )

    log_path = reports_dir / "audit_log.jsonl"

    assert log_path.exists()


def test_audit_event_has_required_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports_dir = tmp_path / "reports"

    monkeypatch.setattr(
        config,
        "reports_dir",
        str(reports_dir),
    )

    record_audit_event(
        action="report_saved",
        detail="Approved report was saved.",
        report_id="report-456",
    )

    log_path = reports_dir / "audit_log.jsonl"
    event = json.loads(
        log_path.read_text(
            encoding="utf-8"
        ).strip()
    )

    assert "timestamp" in event
    assert event["report_id"] == "report-456"
    assert event["action"] == "report_saved"
    assert event["detail"] == "Approved report was saved."
