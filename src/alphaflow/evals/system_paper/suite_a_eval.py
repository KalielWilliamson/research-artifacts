from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from alphaflow.cognition.memory.inmemory_store import InMemoryMemoryStore
from alphaflow.cognition.memory.service import MemoryService, NullMemoryService
from alphaflow.evals.system_paper.embeddings import DeterministicEmbeddingsClient
from experiments.workloads.suite_a_scoring import load_sessions
from infrastructure_domain.memory.age_graph_repository import AgeGraphRepository
from infrastructure_domain.memory.pgvector_repository import PgVectorMemoryRepository


_QUESTION_RE = re.compile(r"Question:\s+where was the item in '(.+)' left\?")


@dataclass(frozen=True)
class SuiteAEvalConfig:
    memory_tier: str
    summary_update_every: int
    summary_max_facts: int
    embedding_dim: int
    longterm_top_k: int
    lambda_weight: float


def _extract_location(fact: str) -> str:
    if " at " not in fact:
        return ""
    location = fact.split(" at ", 1)[-1].rstrip(".")
    return location.strip()


def _expected_from_question(text: str) -> tuple[str, str]:
    match = _QUESTION_RE.search(text)
    if not match:
        return "", ""
    fact = match.group(1)
    return fact, _extract_location(fact)


def _normalize_tier(value: str | None) -> str:
    if value is None:
        return "no-memory"
    raw = value.strip().lower()
    if raw == "recent":
        return "no-memory"
    return raw


def _build_config(case_cfg: dict[str, Any]) -> SuiteAEvalConfig:
    tags = case_cfg.get("tags") or {}
    tier = case_cfg.get("memory_tier") or tags.get("memory_tier") or "no-memory"
    summary_update_every = int(case_cfg.get("summary_update_every") or 3)
    if summary_update_every <= 0:
        summary_update_every = 1
    return SuiteAEvalConfig(
        memory_tier=_normalize_tier(str(tier)),
        summary_update_every=summary_update_every,
        summary_max_facts=int(case_cfg.get("summary_max_facts") or 50),
        embedding_dim=int(case_cfg.get("embedding_dim") or 16),
        longterm_top_k=int(case_cfg.get("longterm_top_k") or 5),
        lambda_weight=float(case_cfg.get("lambda_weight") or 0.2),
    )


def _update_summary(store: InMemoryMemoryStore, session_id: str, facts: list[str], max_facts: int) -> None:
    trimmed = facts[-max_facts:] if max_facts > 0 else facts
    summary = "Facts:\n" + "\n".join(trimmed)
    store.set_summary(session_id, summary)


def _predict_from_summary(summary: str | None, target_fact: str) -> str:
    if not summary or not target_fact:
        return "unknown"
    if target_fact in summary:
        return _extract_location(target_fact) or "unknown"
    return "unknown"


def _predict_from_longterm(
    memory: MemoryService | NullMemoryService,
    *,
    target_fact: str,
    session_id: str,
    limit: int,
    lambda_weight: float,
) -> str:
    if not target_fact:
        return "unknown"
    hits = memory.recall(
        query=target_fact,
        session_id=session_id,
        limit=limit,
        lambda_weight=lambda_weight,
    )
    if not hits:
        return "unknown"
    top = hits[0].text
    return _extract_location(top) or "unknown"


def _build_memory_service(cfg: SuiteAEvalConfig) -> MemoryService | NullMemoryService:
    if cfg.memory_tier not in {"vector", "graph", "hybrid"}:
        return NullMemoryService()
    embeddings = DeterministicEmbeddingsClient(dim=cfg.embedding_dim)
    vectors = PgVectorMemoryRepository(embedding_dim=cfg.embedding_dim)
    graph = AgeGraphRepository() if cfg.memory_tier in {"graph", "hybrid"} else None
    return MemoryService(embeddings=embeddings, vectors=vectors, graph=graph)


def run_suite_a_eval(case_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    dataset_path = case_cfg.get("dataset_path") or "experiments/datasets/suite_a.jsonl"
    cfg = _build_config(case_cfg)
    tags = dict(case_cfg.get("tags") or {})
    tags.setdefault("memory_tier", cfg.memory_tier)

    sessions = load_sessions(dataset_path)
    total = 0
    correct = 0
    drift = 0

    memory = _build_memory_service(cfg)
    for session in sessions:
        session_id = f"{case_cfg.get('id', 'suite-a')}-{session.get('id', 'session')}"
        store = InMemoryMemoryStore()
        facts: list[str] = []
        fact_count = 0
        summary_dirty = False

        for turn in session.get("turns", []):
            if turn.get("role") != "user":
                continue
            text = str(turn.get("text", ""))
            if text.startswith("Remember this:"):
                fact = text.split("Remember this:", 1)[-1].strip()
                if fact:
                    facts.append(fact)
                    fact_count += 1
                    summary_dirty = True
                if cfg.memory_tier in {"vector", "graph", "hybrid"}:
                    memory.add_chunk(session_id=session_id, text=fact, root_id=session_id, meta={"kind": "fact"})
                if cfg.memory_tier in {"summary", "hybrid"} and fact_count % cfg.summary_update_every == 0:
                    _update_summary(store, session_id, facts, cfg.summary_max_facts)
                    summary_dirty = False
                continue
            if text.startswith("Question:"):
                if cfg.memory_tier in {"summary", "hybrid"} and summary_dirty:
                    _update_summary(store, session_id, facts, cfg.summary_max_facts)
                    summary_dirty = False
                target_fact, expected = _expected_from_question(text)
                if not target_fact:
                    continue
                total += 1
                predicted = "unknown"
                if cfg.memory_tier in {"summary", "hybrid"}:
                    predicted = _predict_from_summary(store.get_summary(session_id), target_fact)
                if predicted == "unknown" and cfg.memory_tier in {"vector", "graph", "hybrid"}:
                    predicted = _predict_from_longterm(
                        memory,
                        target_fact=target_fact,
                        session_id=session_id,
                        limit=cfg.longterm_top_k,
                        lambda_weight=cfg.lambda_weight,
                    )
                if predicted == expected and expected:
                    correct += 1
                else:
                    drift += 1
        if cfg.memory_tier in {"summary", "hybrid"} and summary_dirty:
            _update_summary(store, session_id, facts, cfg.summary_max_facts)

    accuracy = (correct / total) if total else 0.0
    faithfulness = accuracy
    drift_rate = (drift / total) if total else 0.0
    metrics = [
        {"metric_name": "suite_a.accuracy", "value": accuracy, "tags": tags},
        {"metric_name": "suite_a.faithfulness", "value": faithfulness, "tags": tags},
        {"metric_name": "suite_a.drift", "value": drift_rate, "tags": tags},
        {"metric_name": "suite_a.questions", "value": float(total), "tags": tags},
        {"metric_name": "case.completed", "value": 1.0, "tags": tags},
    ]
    return metrics
