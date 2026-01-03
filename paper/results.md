# Results (Planned)

## Claim Verification Map

| Claim-ID | Evaluated Claim | Experiment Suite(s) | Primary Metric(s) |
| --- | --- | --- | --- |
| C1 | Tiered memory improves recall/faithfulness vs stateless | [A][suite-a] | acc, faith, drift |
| C2 | Event-driven decoupling improves tail latency/faults vs sync IO | [B][suite-b], [G][graceful] | ttf, errors |
| C3 | Event-sourced execution enables replay/comparability | [C][suite-c] | replay success, artifact match |
| C4 | Event-structured, tiered runs are a useful systems abstraction | [A][suite-a], [B][suite-b], [C][suite-c] | summary anchor |

Suites A-C evaluate the sufficiency claim in Methods by testing recall, robustness, and replay
under fixed token budgets and bounded load.
All suites evaluate under fixed token budgets unless explicitly noted.

[suite-a]: #suite-a-memory-quality
[suite-b]: #suite-b-fault-tolerance
[graceful]: #graceful-degradation
[suite-c]: #suite-c-causal-traceability-and-replay
[modularity]: #modularity
[comparability]: #comparability

### Metrics primer
- Retrieved-context turnover: fraction of retrieved spans replaced per turn (per 1,000 tokens).
  High turnover can improve recall but may reduce replay equivalence without versioned writes.
- Summary overwrite rate: optional diagnostic for summary-tier policies.
- Replay success: event DAG, memory writes, and retrieved context selections match (outputs may vary).
  Turnover is reported to characterize stability-adaptivity tradeoffs, not optimize one direction.

## Suite A – Memory Quality

Suite A evaluates whether tiered memory improves recall and faithfulness under fixed token budgets
relative to stateless and single-tier baselines.
Results below summarize accuracy, faithfulness, drift, and token usage.

<!--CLAIM:C1-->
Summary memory improves recall but does not eliminate drift, indicating a boundary where
compression helps but does not fully substitute for persistent tiers. Vector/graph tiers
reach perfect scores on these relational recall tasks because the benchmarks are designed to
reward structured retrieval; real-world gains depend on retrieval hygiene and schema quality.
Suite A results aggregate repeated runs per condition with fixed seeds and token budgets.

### Suite A – Adversarial Stress Case

We introduce a stress configuration with heavier distractors, shorter budgets, and aggressive
summary truncation to surface failure modes for low-capacity memory tiers. The adversarial case
uses the same scoring pipeline as the baseline suite, but stresses summary retention and
retrieval depth.

![](figures/accuracy_by_tier_adversarial.png)

Table A-1 summarizes ablation deltas against the recent+summary baseline; the full table is
provided in the appendix artifacts.


## Suite B – Fault Tolerance

Suite B evaluates whether decoupling IO, memory, and reasoning via an event bus improves tail
latency, throughput stability, and fault tolerance under load.
Results below summarize latency, throughput, timeouts, and errors under injected failures.

<!--CLAIM:C2-->

Table B-1 summarizes fault severity vs throughput and tail latency.

| scenario | p95 latency (ms) | RPS | errors |
| --- | --- | --- | --- |
| baseline | 172.505 | 8.693 | 43.333 |
| fault-light | 145.917 | 13.674 | 110.200 |
| fault-heavy | 156.604 | 7.936 | 223.553 |

Suite B results aggregate repeated load runs per scenario with fixed decoding parameters.

## Graceful Degradation

Useful artifacts count outputs passing the default predicate
(GENERATE/EVAL events with payload quality = "useful"). Under latency spikes, the system
often produces zero useful artifacts, while cascading failures still yield partial output.
These metrics quantify partial progress when full answers are unavailable.
The predicate is deterministic and rule-based, enabling consistent comparison across runs.
Graceful degradation results aggregate repeated fault injections per scenario.

## Suite C - Causal Traceability and Replay {#suite-c-causal-traceability-and-replay}

Suite C evaluates whether event-sourced execution enables deterministic replay and run-to-run
comparability of agent behavior.
Results below summarize replay success rates and artifact matches.

<!--CLAIM:C3-->
Under cascading failures, traceability remains intact while useful-artifact counts drop,
indicating replay fidelity persists even as output quality degrades.
Suite C results aggregate repeated replay runs per case.

## Modularity

Modularity results are reported separately in Suite M artifacts as illustrative properties,
not primary claims.

## Comparability

Run-to-run comparability results are reported separately in Suite Comp artifacts as
illustrative properties, not primary claims.

Statistical note: synthetic tasks are deterministic, so variance is low and effect sizes can be
inflated; we emphasize directionality and relative deltas over absolute effect magnitudes, and
report effect sizes for completeness only.

Summary table (C1-C3 anchor).
\begin{table}[t]
\centering
\small
\resizebox{\linewidth}{!}{%
\begin{tabular}{lrrrrl}
anchor & accuracy & drift & p95 latency (ms) & rps & replay success \\
\hline
A no-memory (baseline) & 0.000 & 1.000 & - & - & - \\
A hybrid & 1.000 & 0.000 & - & - & - \\
B baseline & - & - & 172.505 & 8.693 & - \\
B fault-heavy & - & - & 156.604 & 7.936 & - \\
C replay & - & - & - & - & 45/45 (hash match) \\
\hline
\end{tabular}
}
\end{table}


Plots/Tables
- Accuracy vs token budget (A1/A2) for recent/summary/vector/graph/hybrid.
- Latency CDFs direct vs event‑bus (B1); throughput and timeout/DLQ bars.
- Backlog vs time and p95 vs time under overload/recovery (B2).
- Failure injection outcomes (B3): resolves, duplicates, DLQ, retries, observability.
- Retrieval hit‑rate and selection rationale summary.
![](figures/accuracy_by_tier.png)
![](figures/latency_summary.png)
![](figures/throughput_errors.png)
![](figures/drift_violin.png)
![](figures/faithfulness_violin.png)
Tabular metric summaries are generated during report runs and stored alongside figures.

\FloatBarrier
## Artifacts

Detailed metrics tables are included in the artifact bundle (CSV/JSON/TeX) and can
be regenerated with the stats pipeline. For readability, we omit the full metrics
table from the main paper and keep the summary anchors above.

### Experiment 3 - Graceful Degradation
Full matrix omitted in draft; final version will include aggregated Table GD-1 in the appendix.

### Experiment 3 – Graceful Degradation
| case | Δtime-to-first | useful-artifacts | notes |
| ---- | ------------- | ---------------- | ----- |
| g-001 | -1.00s | 0 | no useful artifacts |
| g-002 | 0.77s | 135 |  |
| g-003 | 0.07s | 495 |  |
