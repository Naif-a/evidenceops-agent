import asyncio

import pytest

from app.models import (
    ResearchRequest,
    ResearchStatus,
)
from app import orchestrator


class FakeAgent:
    async def run(self, user_msg: str) -> str:
        return "Evidence-grounded test result."


class SlowAgent:
    async def run(self, user_msg: str) -> str:
        await asyncio.sleep(1)
        return "This result should not complete."


@pytest.mark.asyncio
async def test_unapproved_request_awaits_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []

    monkeypatch.setattr(
        orchestrator,
        "build_agent",
        lambda approved_to_save, report_id=None: FakeAgent(),
    )

    monkeypatch.setattr(
        orchestrator,
        "record_audit_event",
        lambda **kwargs: events.append(kwargs),
    )

    request = ResearchRequest(
        question="What controls reduce agent risk?"
    )

    result = await orchestrator.run_research(
        request=request,
        approved_to_save=False,
    )

    assert result.status == (
        ResearchStatus.AWAITING_APPROVAL
    )
    assert result.report_id
    assert len(events) == 2

    assert events[0]["action"] == "research_started"
    assert events[1]["action"] == "research_completed"

    assert (
        events[0]["report_id"]
        == events[1]["report_id"]
        == result.report_id
    )


@pytest.mark.asyncio
async def test_approved_request_preserves_report_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approval_values = []

    def fake_build_agent(
        approved_to_save: bool,
        report_id: str | None = None,
    ) -> FakeAgent:
        approval_values.append(approved_to_save)
        return FakeAgent()

    monkeypatch.setattr(
        orchestrator,
        "build_agent",
        fake_build_agent,
    )

    monkeypatch.setattr(
        orchestrator,
        "record_audit_event",
        lambda **kwargs: None,
    )

    request = ResearchRequest(
        question="What controls govern report saving?"
    )

    result = await orchestrator.run_research(
        request=request,
        approved_to_save=True,
        report_id="report-123",
    )

    assert result.report_id == "report-123"
    assert result.status == ResearchStatus.APPROVED
    assert approval_values == [True]


@pytest.mark.asyncio
async def test_new_request_gets_new_report_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        orchestrator,
        "build_agent",
        lambda approved_to_save, report_id=None: FakeAgent(),
    )

    monkeypatch.setattr(
        orchestrator,
        "record_audit_event",
        lambda **kwargs: None,
    )

    request = ResearchRequest(
        question="What controls reduce retrieval risk?"
    )

    first = await orchestrator.run_research(
        request=request,
        approved_to_save=False,
    )

    second = await orchestrator.run_research(
        request=request,
        approved_to_save=False,
    )

    assert first.report_id != second.report_id


@pytest.mark.asyncio
async def test_agent_timeout_is_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []

    monkeypatch.setattr(
        orchestrator,
        "build_agent",
        lambda approved_to_save, report_id=None: SlowAgent(),
    )

    monkeypatch.setattr(
        orchestrator,
        "record_audit_event",
        lambda **kwargs: events.append(kwargs),
    )

    monkeypatch.setattr(
        orchestrator.config,
        "agent_timeout_seconds",
        0.01,
    )

    request = ResearchRequest(
        question="What happens when execution takes too long?"
    )

    with pytest.raises(
        RuntimeError,
        match="exceeded",
    ):
        await orchestrator.run_research(
            request=request,
            approved_to_save=False,
        )

    assert events[-1]["action"] == "research_failed"


@pytest.mark.asyncio
async def test_prompt_contains_execution_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_prompts = []

    class CapturingAgent:
        async def run(
            self,
            user_msg: str,
        ) -> str:
            captured_prompts.append(user_msg)
            return "Completed."

    monkeypatch.setattr(
        orchestrator,
        "build_agent",
        lambda approved_to_save, report_id=None: CapturingAgent(),
    )

    monkeypatch.setattr(
        orchestrator,
        "record_audit_event",
        lambda **kwargs: None,
    )

    request = ResearchRequest(
        question="How is agent execution bounded?"
    )

    await orchestrator.run_research(
        request=request,
        approved_to_save=False,
    )

    assert captured_prompts
    assert (
        str(orchestrator.config.max_tool_calls)
        in captured_prompts[0]
    )
    assert "save_report tool is unavailable" in (
        captured_prompts[0]
    )
