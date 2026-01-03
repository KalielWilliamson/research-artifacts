# Experiments

## Suite A: Memory quality under token budgets

### A1) Synthetic multi‑turn recall benchmark
Tasks: Carryover facts, Chained entities (A→B→C), Episodic timeline, Distractor overload.
These tasks surface failure modes and control for budgets rather than approximate real user
distributions.
Conditions: recent only; summary only; vector only (when ready); graph only (when ready); hybrid.
Report: accuracy, faithfulness, context tokens (mean/p95), retrieval hit rate.
Plot: Accuracy vs token budget.

### A2) Budget clamp (fixed 2k/4k/8k)
Clamp context size; measure degradation across policies.

### A3) Stability over long sessions
200–500 turns with periodic queries; drift, forgetting vs summary_interval/keep_tail; contradiction rate.

## Suite B: Systems reliability + tail latency

### B1) Direct vs event‑bus under load
Latency CDFs (p50/p95/p99), throughput, timeouts, SSE errors, backlog.

### B2) Backpressure and queue behavior
Overload then recovery; backlog vs time, p95 vs time, DLQ counts.

### B3) Failure injection matrix
LLM delay/errors, dropped replies, Redis write failure, worker crash, duplicate delivery. Evaluate resolves/duplicates/DLQ/retries/observability.

## Suite C: Reproducibility + CI gates

### C1) Deterministic e2e round‑trip
Stub model; validate correlation, persistence, summary updates, reply_to.

### C2) Metrics contract tests
Assert counters/histograms exist and increment under induced failures; health reflects degradation.

### C3) One‑command reproduction
Compose overlay; small A1 + B3 slice; write plots + JSON artifacts.
