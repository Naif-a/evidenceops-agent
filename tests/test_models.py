import pytest
from pydantic import ValidationError

from app.models import ResearchRequest


def test_valid_research_request() -> None:
    request = ResearchRequest(
        question="What controls reduce agent risks?",
        audience="Governance team",
    )

    assert request.question == (
        "What controls reduce agent risks?"
    )
    assert request.audience == "Governance team"


def test_question_whitespace_is_normalized() -> None:
    request = ResearchRequest(
        question="What   controls   reduce agent risks?"
    )

    assert request.question == (
        "What controls reduce agent risks?"
    )


def test_overly_broad_question_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(
            question="Tell me everything"
        )


def test_short_question_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(question="Agent risks")
