# Research Agent Operational Procedure

## Draft Stage

The agent receives a specific research objective, decomposes it into subproblems, retrieves relevant evidence, and produces a draft.

## Approval Stage

The user reviews the draft. Until explicit approval is received, the agent must not save the report.

## Save Stage

After approval, the report is saved only inside the reports directory. The filename must be sanitized to prevent path traversal.

## Audit Stage

The system records events before and after consequential actions. Failed actions must also be recorded with an appropriate status and explanation.
