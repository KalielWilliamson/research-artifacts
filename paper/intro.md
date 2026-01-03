# Introduction

## Motivation

Conversational agents deployed in practice must recall information across turns while remaining
reliable under load and observable in production. Monolithic agents entangle IO, memory, and
reasoning, which complicates scaling, testing, and diagnosis.
This paper does not propose a new memory algorithm; it evaluates whether architectural
decoupling and tiered memory are sufficient for the behaviors studied here.

This paper examines three questions: (i) whether tiered memory improves recall and
faithfulness under fixed token budgets relative to stateless and single-tier baselines, (ii)
whether event-driven decoupling improves tail latency and fault tolerance under load relative
to direct synchronous IO, and (iii) whether event-sourced execution enables deterministic
replay and run-to-run comparability.
Because memory selection, persistence, and retrieval are mediated through replayable events,
tiered memory policies can be evaluated under fixed token budgets with stable semantics across runs.

While memory systems, agent observability, and replay have prior art independently, this work
targets their composition into a replayable, comparable agent execution artifact with measured
reliability and memory behavior.
In deployed agents these concerns interact: load and failure modes affect memory semantics, and
replayability depends on how memory is persisted and retrieved, so we evaluate them jointly.

## Thesis

**Thesis.** <!--CLAIM:C4-->

## Contributions

- Modular event‑bus design separating IO, memory, reasoning.
- Hybrid memory policy (recent/summary, vector/graph as extensions).
- First‑class observability (metrics, CI gates) and reproducible artifact.

## Design Motivation (Constraints‑First)

Under bounded context budgets, failure modes (timeouts, dropped replies), and the need for
reproducible observability, a synchronous monolith is a poor abstraction for conversational
agents. Decoupling IO, memory, and reasoning via an event‑driven transport makes the
request/response contract explicit, enables buffering and backpressure, and isolates failures.
While these mechanisms are standard in distributed systems, they are rarely evaluated or
reported in agent architectures, where synchronous designs still dominate.

Given these constraints, a Gateway + worker ("Cognition Bridge") over a stream transport is a
natural fit. The memory subsystem is treated as a first‑class, pluggable component: a bounded
recent buffer and rolling summary form the minimal tier, with vector and graph recall layered
as optional extensions. A simple hybrid retrieval policy surfaces the right context at fixed
token budgets, while metrics (latency CDFs, timeouts, DLQ counts, backlog) make behavior
measurable in CI and operations. The remainder of this paper presents the architecture and
its empirical properties under these constraints.
