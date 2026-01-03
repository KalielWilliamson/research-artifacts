# Methods

## Architecture
- Gateway (FastAPI): HTTP + SSE; env‑toggled direct vs event‑bus.
- Cognition Bridge: consumes commands, composes context, calls LLM, persists memory, responds by correlation_id.
- Memory tiers: Redis recent + summary; vector (pgvector) and graph (Neo4j) as optional extensions.
- Hybrid retrieval policy: configurable weights; logs selection rationale.

### Sufficiency Claim
We claim that an event-driven blackboard with tiered memory supports the behaviors evaluated
in this paper: multi-turn recall, controlled retrieval, and traceable execution under fixed
token budgets and bounded system load.

### Non-Goals
- Real-time humanoid robotics; we focus on text-bound agents with bounded latency budgets.
- Lifelong learning beyond fixed horizons; experiments cover bounded run windows only.
- Agent self-modification; we measure behavior under fixed policies and components.
- RLHF or online preference optimization; training is out of scope for this paper.
- Scaling beyond 100 concurrent agents; we evaluate single-agent and small-fanout regimes.
- Open-ended tool discovery; tools are predeclared and externally orchestrated.
- Continuous deployment reliability; we only assert reproducibility within controlled runs.

### Blackboard Motivation
Classical blackboard systems (BB1 1980, BB2 1983, BB3 1986, BB4 1988) separated knowledge
sources, control, and shared state. We adopt that separation but replace synchronous control
with an event-driven execution model to keep coordination traceable and testable.

| Aspect | Event-Driven Blackboard | Task Queue | Micro-Service Graph |
| --- | --- | --- | --- |
| Coordination | Shared event log + policy layer | Loose work dispatch | Service-to-service contracts |
| Traceability + replay | First-class DAG + artifacts | Limited without extra tooling | Distributed tracing needed |
| Adaptation | Policy swaps without rewrites | Queue workers fixed | Cross-service changes required |
| Observability | Unified metrics + replay | Per-worker logs | Multi-system aggregation |

![System architecture overview](figures/architecture.png)
_Figure: Event-driven gateway, bus, and cognition bridge with memory tiers._

## Agents and Conditions
- Baseline (Implicit): direct LLM, no persistence.
- Epistemic (Event‑Bus): recent+summary; later add vector/graph per ablation.
- Identical models/compute across conditions; bounded token budgets.

## Datasets/Tasks
- Synthetic multi‑turn families: carryover facts, chained entities (A→B→C), episodic timelines, distractor overload.
- Optional small knowledge‑grounded slice for vector/graph tiers.

## Metrics
- Answer accuracy; faithfulness (no invention via traps); retrieval hit rate.
- Context tokens used (mean/p95); latency CDFs; timeout/DLQ rates; backlog proxy.
- Retrieved-context turnover (fraction of retrieved spans replaced per turn, per 1,000 tokens).
- Summary overwrite rate (optional diagnostic for tier policies).

### Evaluation Protocol
- Runs per condition: Suites A/B repeat 5 runs with seed offsets 0-4; Suite C repeats 3 runs.
- Decoding: temperature 0.0 and max_tokens 256 unless suite configs override.
- Token budget: prompt assembly enforces fixed budgets; context_tokens_used is logged.
- Load warm-up: 0 seconds to include cold-start behavior typical of bursty traffic.
- Failures: timeouts, HTTP 5xx, missing replies, DLQ entries, and duplicate responses.
- Memory write outcomes (committed/rolled back/duplicate) are logged to separate retrieval effects
  from execution artifacts under failure.
- Replay evaluation: deterministic replay for stubbed runs; trace replay for real model calls.
- Replay success: event DAG, memory writes, and retrieved context selections match; outputs may vary.
