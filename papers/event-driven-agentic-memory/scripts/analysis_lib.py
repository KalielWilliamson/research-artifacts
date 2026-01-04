from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stats_lib import bootstrap_ci, cliffs_delta, cohens_d, ks_test, mann_whitney_u, mean, median, std


REQUIRED_TIERS = {"no-memory", "summary", "vector", "graph", "hybrid"}


@dataclass(frozen=True)
class MetricGroup:
    suite: str
    metric_name: str
    tags: dict[str, str]
    values: list[float]
    run_ids: list[str]


def _canonical_tier(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip().lower()
    if raw == "recent":
        return "no-memory"
    return raw


def _normalize_tags(tags: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in tags.items():
        normalized[str(key)] = str(value)
    tier = normalized.get("memory_tier")
    if tier is not None:
        normalized["memory_tier"] = _canonical_tier(tier) or tier
    return normalized


def load_metrics(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"metrics file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _group_metrics(records: list[dict[str, Any]]) -> list[MetricGroup]:
    groups: dict[tuple[str, str, tuple[tuple[str, str], ...]], MetricGroup] = {}
    for record in records:
        suite = str(record.get("suite") or "")
        metric_name = str(record.get("metric_name") or "")
        run_id = str(record.get("run_id") or "")
        tags = _normalize_tags(record.get("tags") or {})
        key = (suite, metric_name, tuple(sorted(tags.items())))
        if key not in groups:
            groups[key] = MetricGroup(suite=suite, metric_name=metric_name, tags=tags, values=[], run_ids=[])
        groups[key].values.append(float(record.get("value") or 0.0))
        if run_id:
            groups[key].run_ids.append(run_id)
    return list(groups.values())


def _validate_baselines(groups: list[MetricGroup]) -> None:
    tiers = {
        g.tags.get("memory_tier")
        for g in groups
        if g.suite == "A" and g.metric_name.startswith("suite_a.") and g.tags.get("memory_tier")
    }
    if tiers:
        missing = REQUIRED_TIERS.difference(tiers)
        if missing:
            raise ValueError(f"Missing required memory tiers in Suite A metrics: {sorted(missing)}")


def _group_key_without(tags: dict[str, str], drop: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((k, v) for k, v in tags.items() if k != drop))


def _build_comparisons(groups: list[MetricGroup]) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str, tuple[tuple[str, str], ...], str], MetricGroup] = {}
    for group in groups:
        if "memory_tier" in group.tags:
            base = _group_key_without(group.tags, "memory_tier")
            tier = group.tags.get("memory_tier") or ""
            by_key[(group.suite, group.metric_name, base, f"tier:{tier}")] = group
        elif "scenario" in group.tags:
            base = _group_key_without(group.tags, "scenario")
            scenario = group.tags.get("scenario") or ""
            by_key[(group.suite, group.metric_name, base, f"scenario:{scenario}")] = group

    def _get_group(suite: str, metric: str, base: tuple[tuple[str, str], ...], key: str) -> MetricGroup | None:
        return by_key.get((suite, metric, base, key))

    for (suite, metric, base, label), group in list(by_key.items()):
        if label.startswith("tier:"):
            baseline = _get_group(suite, metric, base, "tier:no-memory")
            if not baseline or baseline is group:
                continue
        elif label.startswith("scenario:"):
            baseline = _get_group(suite, metric, base, "scenario:baseline")
            if not baseline or baseline is group:
                continue
        else:
            continue

        comp = {
            "suite": suite,
            "metric_name": metric,
            "baseline_tags": baseline.tags,
            "compare_tags": group.tags,
            "cohens_d": cohens_d(group.values, baseline.values),
            "cliffs_delta": cliffs_delta(group.values, baseline.values),
        }
        mw = mann_whitney_u(group.values, baseline.values)
        ks = ks_test(group.values, baseline.values)
        comp["p_mann_whitney"] = mw.p_value
        comp["p_ks"] = ks.p_value
        comparisons.append(comp)
    return comparisons


def aggregate_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups = _group_metrics(records)
    _validate_baselines(groups)
    summary: list[dict[str, Any]] = []
    for group in groups:
        ci_low, ci_high = bootstrap_ci(group.values, stat="mean")
        summary.append(
            {
                "suite": group.suite,
                "metric_name": group.metric_name,
                "tags": group.tags,
                "n": len(group.values),
                "mean": mean(group.values),
                "median": median(group.values),
                "std": std(group.values),
                "ci_low": ci_low,
                "ci_high": ci_high,
                "values": group.values,
                "run_ids": sorted(set(group.run_ids)),
            }
        )
    comparisons = _build_comparisons(groups)
    return {
        "groups": summary,
        "comparisons": comparisons,
    }
