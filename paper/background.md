# Background and Related Work

## Memory‑Augmented Agents and RAG
- Episodic buffers, learned controllers, retrieval‑augmented generation.
- Strengths: improved recall; Challenges: budgets, reliability, observability.
Retrieval-augmented generation and dense retrieval are standard mechanisms for improving recall
under token and knowledge constraints and motivate external memory tiers. <!--CLAIM:PA3-->
Efficient vector search infrastructure makes dense retrieval practical at scale. <!--CLAIM:PA4-->

## Graph‑Enhanced Retrieval
- Knowledge graphs improve relational queries and multi‑hop recall.
- Operational complexity motivates modular, optional integration.
Graph-based retrieval is a standard extension of RAG pipelines and supports structured recall.
<!--CLAIM:PA5-->

## Systems for LLM Ops
- Service decomposition, backpressure, and metrics are under‑reported in agent papers.
- Our focus: event bus decoupling and first‑class observability.
Recent scaling studies show that coordination topology interacts with task regime and model
capability, suggesting that execution abstractions must remain viable across diverse workloads.
<!--CLAIM:C5-->

## Summarization Drift and Long Context
Summaries and long-context processing can introduce factual drift and hallucination, motivating
explicit memory tier boundaries and diagnostics. <!--CLAIM:PA6-->

## Event Logs and Replay
Event logs and event sourcing support reconstructability and replay as established systems
patterns for stateful services. <!--CLAIM:PA7-->
Logical clocks and causal ordering provide a mathematical foundation for attributing distributed
events in event-oriented systems. <!--CLAIM:PA12-->

## Observability and Tracing
Distributed tracing and context propagation are standard requirements for correlating events
across services in reliable systems. <!--CLAIM:PA8-->

## Tail Latency and Fault Injection
Tail latency percentiles dominate user-visible reliability in large-scale services.
<!--CLAIM:PA9-->
Fault injection and chaos engineering are established methodologies for evaluating resilience.
<!--CLAIM:PA10-->

## Credit Assignment in Multi-Agent Systems
Credit assignment remains a core challenge in temporally extended multi-agent decision settings,
and surveys identify it as central and unresolved. <!--CLAIM:PA1-->
Open-agent settings (agent/task/type churn) further increase attribution ambiguity via
non-stationarity and shifting participation. <!--CLAIM:PA2-->
