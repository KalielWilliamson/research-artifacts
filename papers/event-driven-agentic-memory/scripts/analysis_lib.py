from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stats_lib import (
    benjamini_hochberg,
    bootstrap_ci,
    cliffs_delta,
    cohens_d,
    ks_test,
    mann_whitney_u,
    mean,
    median,
    required_n_two_sample_t,
    std,
)


REQUIRED_TIERS = {"no-memory", "summary", "vector", "graph", "hybrid"}
VOLATILE_TAG_KEYS = {
    "run_name",
    "source_run_id",
    "source_uid",
    "step",
    "snapshot_id",
    "snapshot_created_at",
}
DEFAULT_PRIMARY_METRICS = (
    "suite_a.accuracy",
    "suite_a.drift",
    "load.p95_ms",
    "load.errors",
    "completion.hash",
    "degradation.time_to_first_useful",
)


@dataclass(frozen=True)
class MetricGroup:
    suite: str
    metric_name: str
    tags: dict[str, str]
    values: list[float]
    run_ids: list[str]


@dataclass(frozen=True)
class FrequentistProtocolConfig:
    alpha: float = 0.05
    apply_fdr: bool = True
    power_target: float = 0.8
    min_effect_size_d: float = 0.3
    primary_metrics: tuple[str, ...] = DEFAULT_PRIMARY_METRICS


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
        key_str = str(key)
        if key_str in VOLATILE_TAG_KEYS:
            continue
        normalized[key_str] = str(value)
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
            "n_baseline": len(baseline.values),
            "n_compare": len(group.values),
            "mean_baseline": mean(baseline.values),
            "mean_compare": mean(group.values),
            "delta_mean": mean(group.values) - mean(baseline.values),
            "cohens_d": cohens_d(group.values, baseline.values),
            "cliffs_delta": cliffs_delta(group.values, baseline.values),
        }
        mw = mann_whitney_u(group.values, baseline.values)
        ks = ks_test(group.values, baseline.values)
        comp["p_mann_whitney"] = mw.p_value
        comp["p_ks"] = ks.p_value
        comparisons.append(comp)
    return comparisons


def _annotate_frequentist_protocol(
    comparisons: list[dict[str, Any]],
    *,
    config: FrequentistProtocolConfig,
) -> dict[str, Any]:
    primary_set = set(config.primary_metrics)
    for comp in comparisons:
        comp["is_primary"] = str(comp.get("metric_name") or "") in primary_set

    pvals_all = [comp.get("p_mann_whitney") for comp in comparisons]
    adj_all = benjamini_hochberg(pvals_all) if config.apply_fdr else pvals_all
    for comp, p_adj in zip(comparisons, adj_all):
        comp["p_mann_whitney_adj"] = p_adj
        comp["significant"] = bool(p_adj is not None and p_adj <= config.alpha)

    primary_comps = [comp for comp in comparisons if comp.get("is_primary")]
    pvals_primary = [comp.get("p_mann_whitney") for comp in primary_comps]
    adj_primary = benjamini_hochberg(pvals_primary) if config.apply_fdr else pvals_primary
    for comp, p_adj in zip(primary_comps, adj_primary):
        comp["p_mann_whitney_primary_adj"] = p_adj
        comp["primary_significant"] = bool(p_adj is not None and p_adj <= config.alpha)

    power_rows: list[dict[str, Any]] = []
    recommended_runs = 1
    for comp in primary_comps:
        observed_d = abs(float(comp.get("cohens_d") or 0.0))
        target_d = max(observed_d, float(config.min_effect_size_d))
        n_required = required_n_two_sample_t(
            effect_size_d=target_d,
            alpha=float(config.alpha),
            power=float(config.power_target),
        )
        n_current = int(min(int(comp.get("n_baseline", 0)), int(comp.get("n_compare", 0))))
        if n_required is not None:
            recommended_runs = max(recommended_runs, int(n_required))
        power_rows.append(
            {
                "suite": comp.get("suite", ""),
                "metric_name": comp.get("metric_name", ""),
                "compare_tags": comp.get("compare_tags", {}),
                "n_current": n_current,
                "effect_size_observed_d": observed_d,
                "effect_size_target_d": target_d,
                "alpha": float(config.alpha),
                "power_target": float(config.power_target),
                "n_required_per_group": n_required,
                "is_power_sufficient": bool(n_required is not None and n_current >= n_required),
            }
        )

    return {
        "config": {
            "alpha": float(config.alpha),
            "apply_fdr": bool(config.apply_fdr),
            "power_target": float(config.power_target),
            "min_effect_size_d": float(config.min_effect_size_d),
            "primary_metrics": list(config.primary_metrics),
        },
        "counts": {
            "comparisons_total": len(comparisons),
            "comparisons_primary": len(primary_comps),
        },
        "run_recommendation": {
            "recommended_runs_per_condition": int(recommended_runs),
            "basis": "max required n across primary outcomes using two-sample power approximation",
        },
        "power_table": power_rows,
    }


def aggregate_metrics(
    records: list[dict[str, Any]],
    *,
    protocol_config: FrequentistProtocolConfig | None = None,
) -> dict[str, Any]:
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
    protocol = _annotate_frequentist_protocol(
        comparisons,
        config=protocol_config or FrequentistProtocolConfig(),
    )
    return {
        "groups": summary,
        "comparisons": comparisons,
        "frequentist_protocol": protocol,
    }
