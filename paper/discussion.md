# Discussion

- Hybrid memory benefits vs single‑tier under budgets; where summary helps; when vector/graph add value.
- Reliability: event decoupling stabilizes tails; observability turns failures into specs.
- Policy tuning: weights, K, and summary intervals; diminishing returns and cost.
Observability relies on standard tracing and context propagation for correlating events across
services. <!--CLAIM:PA8-->
Tail latency percentiles remain the dominant reliability signal for user-facing systems.
<!--CLAIM:PA9-->

Execution topology governs whether agent coordination strategies remain operable, measurable,
and trustworthy as systems scale across task regimes. <!--CLAIM:C6-->
Replayable event traces are a prerequisite for rigorous credit-assignment analysis in the
regimes where such analysis is meaningful; they enable causal attribution without implying
we solve credit assignment itself. <!--CLAIM:D1-->
