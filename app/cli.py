import asyncio

from pydantic import ValidationError

from app.models import ResearchRequest
from app.orchestrator import run_research


def display_result(title: str, result) -> None:
    """Display a research result clearly in the terminal."""

    print(f"\n{'=' * 60}")
    print(title)
    print(f"{'=' * 60}")
    print(f"Report ID: {result.report_id}")
    print(f"Status: {result.status.value}")
    print(f"\n{result.result}")


async def main() -> None:
    print("=" * 60)
    print("EvidenceOps Agent")
    print("Governed, evidence-based research assistant")
    print("Type 'exit' to stop")
    print("=" * 60)

    while True:
        question = input("\nResearch question: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("EvidenceOps Agent stopped.")
            break

        audience = input(
            "Intended audience [general]: "
        ).strip()

        if not audience:
            audience = "general"

        try:
            request = ResearchRequest(
                question=question,
                audience=audience,
                require_approval=True,
            )

            draft = await run_research(
                request=request,
                approved_to_save=False,
            )

            display_result("RESEARCH DRAFT", draft)

            approval = input(
                "\nApprove and save this report? [y/N]: "
            ).strip().lower()

            if approval == "y":
                print("\nRunning approved report workflow...")

                final_result = await run_research(
                    request=request,
                    approved_to_save=True,
                    report_id=draft.report_id,
                )

                display_result(
                    "APPROVED RESEARCH RESULT",
                    final_result,
                )
            else:
                print(
                    "\nReport was not approved. "
                    "No Markdown report was saved."
                )

        except ValidationError as exc:
            print("\nInvalid research request:")

            for error in exc.errors():
                print(f"- {error['msg']}")

        except KeyboardInterrupt:
            print("\nOperation cancelled.")

        except Exception as exc:
            print(
                f"\nResearch failed: "
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    asyncio.run(main())