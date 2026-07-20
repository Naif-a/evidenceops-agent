import asyncio

from fastapi import FastAPI, HTTPException, status

from app.models import ResearchRequest, ResearchResult
from app.orchestrator import run_research


app = FastAPI(
    title="EvidenceOps Agent API",
    description=(
        "A governed, evidence-based research agent "
        "built with LlamaIndex."
    ),
    version="1.0.0",
)


# Stores reports waiting for approval.
# A production system should use a persistent database.
pending_requests: dict[str, ResearchRequest] = {}
pending_lock = asyncio.Lock()


@app.get("/health")
def health() -> dict[str, str]:
    """Return the API health status."""

    return {"status": "ok"}


@app.post(
    "/research",
    response_model=ResearchResult,
    status_code=status.HTTP_200_OK,
)
async def create_research_draft(
    request: ResearchRequest,
) -> ResearchResult:
    """Create a research draft without saving permission."""

    # The API always requires approval.
    safe_request = request.model_copy(
        update={"require_approval": True}
    )

    try:
        draft = await run_research(
            request=safe_request,
            approved_to_save=False,
        )

        async with pending_lock:
            pending_requests[draft.report_id] = safe_request

        return draft

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Research execution failed.",
        ) from exc


@app.post(
    "/research/{report_id}/approve",
    response_model=ResearchResult,
    status_code=status.HTTP_200_OK,
)
async def approve_research_report(
    report_id: str,
) -> ResearchResult:
    """Approve and save one pending report."""

    async with pending_lock:
        request = pending_requests.pop(report_id, None)

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Pending report not found, already approved, "
                "or no longer available."
            ),
        )

    try:
        return await run_research(
            request=request,
            approved_to_save=True,
            report_id=report_id,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Approved research execution failed.",
        ) from exc


@app.delete(
    "/research/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reject_research_report(
    report_id: str,
) -> None:
    """Reject and remove one pending report."""

    async with pending_lock:
        request = pending_requests.pop(report_id, None)

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending report not found.",
        )