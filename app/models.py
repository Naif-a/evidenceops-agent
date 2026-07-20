from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ResearchStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    FAILED = "failed"


class ResearchRequest(BaseModel):
    question: str = Field(min_length=10, max_length=1000)
    audience: str = Field(
        default="general",
        min_length=2,
        max_length=100,
    )
    require_approval: bool = True

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        question = " ".join(value.split())

        if len(question.split()) < 3:
            raise ValueError(
                "The research objective must contain at least "
                "three words."
            )

        broad_requests = {
            "tell me everything",
            "research everything",
            "analyze everything",
            "do some research",
        }

        if question.lower() in broad_requests:
            raise ValueError(
                "The research objective is too broad."
            )

        return question


class ResearchResult(BaseModel):
    report_id: str
    status: ResearchStatus
    result: str