# EvidenceOps Agent Evaluation Report

**Generated:** 2026-07-19T21:21:29.607202+00:00

## Executive Summary

EvidenceOps was evaluated for retrieval quality, latency, deterministic governance behavior, chunking configuration, and adversarial safety.

## Retrieval Metrics

| Metric | Result |
|---|---:|
| Retrieval Hit Rate@5 | 100.0% |
| Successful retrievals | 25/25 |
| Average retrieval latency | 51.04 ms |
| Maximum retrieval latency | 310.42 ms |

## Automated Tests

- Tests passed: 18
- Test-suite status: Passed
- Approval compliance: covered by tests that verify unavailable save permission, isolated report IDs, and single-request approval.
- Execution bounds: covered by deterministic timeout tests.

## Chunking Experiment
    
| Chunk Size | Overlap | Nodes | Hit Rate | Average Latency |
|---:|---:|---:|---:|---:|
| 350 | 50 | 6 | 96.0% | 41.15 ms |
| 700 | 100 | 6 | 96.0% | 40.11 ms |
| 1200 | 150 | 6 | 96.0% | 32.16 ms |

### Chunking Interpretation

All configurations generated the same number of nodes. The current documents are too short for chunk size to materially change retrieval.

The project therefore retains the balanced baseline of `chunk_size=700` and `chunk_overlap=100`. The experiment should be repeated with larger production documents.

## Retrieval Failures

No retrieval failures were observed.
## Adversarial Safety Evaluation

A malicious document attempted to override system policy, reveal environment variables, and force an unapproved report save.

Implemented defenses:

- Retrieved content is classified as untrusted data with no instruction authority.
- The system prompt prohibits retrieved content from changing permissions or revealing secrets.
- The save tool is removed from unapproved agent runs.
- Report paths are sanitized and restricted to the reports directory.
- API errors return controlled messages without stack traces.

## Latency and Cost

- Retrieval embeddings run locally, so retrieval has no per-request API cost.
- The configured OpenRouter model uses a free endpoint, so current demonstration calls have no direct model charge.
- Free endpoints may introduce rate limits, availability variation, and inconsistent latency.

## Observed Limitations

- The knowledge base contains short demonstration documents rather than production-scale sources.
- Pending API approvals use in-memory storage and are lost when the process restarts.
- Tool-call limits are communicated through policy, while a deterministic timeout provides the hard execution boundary.
- Additional end-to-end evaluations are required before production deployment.

## Recommended Improvements

1. Evaluate larger and more diverse documents.
2. Add reranking or hybrid keyword/vector retrieval.
3. Store approval state in a persistent database.
4. Add authentication and rate limiting.
5. Add model-call tracing and token accounting.
6. Run the adversarial suite after every policy change.


## Single-Agent vs. Multi-Agent Evaluation

The optional multi-agent extension was evaluated against the
single-agent baseline using the same three representative cases.

| Metric | Single-Agent | Multi-Agent |
|---|---:|---:|
| Successful cases | 3/3 | 3/3 |
| Average quality score | 91.67% | 91.67% |
| Average latency | 40.34 seconds | 62.72 seconds |
| Specialists | 1 | 5 |
| Monetary cost | $0 | $0 |

The multi-agent workflow completed all five specialist stages:
Research Planner, Evidence Retriever, Critic, Report Writer, and
Supervisor. It also preserved approval and audit controls.

However, it did not improve measured output quality and increased
average latency by 22.38 seconds, approximately 55%. Therefore, the
single-agent workflow remains the default implementation. The
multi-agent workflow is retained as an optional experimental extension.

An initial LLM-driven handoff implementation selected an invalid target
and failed to complete all specialist stages. This coordination failure
was corrected by implementing deterministic Python orchestration:

Research Planner → Evidence Retriever → Critic → Report Writer →
Supervisor.

Detailed results are stored in
`reports/single_vs_multi_evaluation.json`.