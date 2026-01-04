from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def _load_analysis(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, Any], data)


def _save_fig(fig: Figure, out_dir: Path, name: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(out_dir / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def _group_by(
    groups: list[dict[str, Any]],
    metric_name: str,
    suite: str,
    scenario: str | None = None,
) -> list[dict[str, Any]]:
    filtered = [g for g in groups if g.get("metric_name") == metric_name and g.get("suite") == suite]
    if scenario is None:
        return filtered
    return [g for g in filtered if g.get("tags", {}).get("scenario") == scenario]


def _tier_order(values: list[str]) -> list[str]:
    order = ["no-memory", "summary", "vector", "graph", "hybrid"]
    return [v for v in order if v in values] + [v for v in values if v not in order]


def plot_accuracy_by_tier(
    groups: list[dict[str, Any]],
    out_dir: Path,
    *,
    scenario: str | None = None,
    title: str = "Suite A Accuracy by Memory Tier",
    out_name: str = "accuracy_by_tier",
) -> None:
    suite_groups = _group_by(groups, "suite_a.accuracy", "A", scenario)
    if not suite_groups:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.text(0.5, 0.5, "No Suite A accuracy data", ha="center", va="center")
        ax.set_axis_off()
        _save_fig(fig, out_dir, out_name)
        return
    tiers = [g["tags"].get("memory_tier", "") for g in suite_groups]
    tiers = _tier_order(sorted(set(tiers)))
    means: list[float] = []
    errs: list[list[float]] = []
    for tier in tiers:
        g = next((x for x in suite_groups if x["tags"].get("memory_tier") == tier), None)
        if not g:
            continue
        mean_val = float(g.get("mean", 0.0))
        means.append(mean_val)
        ci = (g.get("ci_low", 0.0), g.get("ci_high", 0.0))
        errs.append([mean_val - float(ci[0]), float(ci[1]) - mean_val])
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(tiers, means, yerr=list(zip(*errs, strict=False)), capsize=4, color="#2d6a4f")
    ax.set_ylabel("Accuracy")
    ax.set_title(title)
    ax.set_ylim(0, 1.05)
    _save_fig(fig, out_dir, out_name)


def plot_latency_summary(groups: list[dict[str, Any]], out_dir: Path) -> None:
    avg_groups = _group_by(groups, "load.avg_ms", "B")
    p95_groups = _group_by(groups, "load.p95_ms", "B")
    if not avg_groups or not p95_groups:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.text(0.5, 0.5, "No Suite B latency data", ha="center", va="center")
        ax.set_axis_off()
        _save_fig(fig, out_dir, "latency_summary")
        return
    scenarios = sorted({g["tags"].get("scenario", "") for g in avg_groups})
    avg = [
        float(next((g for g in avg_groups if g["tags"].get("scenario") == s), {}).get("mean", 0.0))
        for s in scenarios
    ]
    p95 = [
        float(next((g for g in p95_groups if g["tags"].get("scenario") == s), {}).get("mean", 0.0))
        for s in scenarios
    ]
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(scenarios))
    ax.bar([i - 0.2 for i in x], avg, width=0.4, label="avg", color="#40916c")
    ax.bar([i + 0.2 for i in x], p95, width=0.4, label="p95", color="#74c69d")
    ax.set_xticks(list(x))
    ax.set_xticklabels(scenarios)
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Suite B Latency Summary")
    ax.legend()
    _save_fig(fig, out_dir, "latency_summary")


def plot_throughput_errors(groups: list[dict[str, Any]], out_dir: Path) -> None:
    rps_groups = _group_by(groups, "load.rps", "B")
    err_groups = _group_by(groups, "load.errors", "B")
    req_groups = _group_by(groups, "load.requests", "B")
    if not rps_groups or not err_groups or not req_groups:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.text(0.5, 0.5, "No Suite B throughput data", ha="center", va="center")
        ax.set_axis_off()
        _save_fig(fig, out_dir, "throughput_errors")
        return
    scenarios = sorted({g["tags"].get("scenario", "") for g in rps_groups})
    rps = [
        float(next((g for g in rps_groups if g["tags"].get("scenario") == s), {}).get("mean", 0.0))
        for s in scenarios
    ]
    err_rate = []
    for s in scenarios:
        errs = float(next((g for g in err_groups if g["tags"].get("scenario") == s), {}).get("mean", 0.0))
        reqs = float(next((g for g in req_groups if g["tags"].get("scenario") == s), {}).get("mean", 0.0))
        err_rate.append(errs / reqs if reqs else 0.0)
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(scenarios))
    ax.bar([i - 0.2 for i in x], rps, width=0.4, label="RPS", color="#1b4332")
    ax.bar([i + 0.2 for i in x], err_rate, width=0.4, label="Error rate", color="#e76f51")
    ax.set_xticks(list(x))
    ax.set_xticklabels(scenarios)
    ax.set_ylabel("RPS / Error rate")
    ax.set_title("Suite B Throughput and Error Rate")
    ax.legend()
    _save_fig(fig, out_dir, "throughput_errors")


def plot_violin(
    groups: list[dict[str, Any]],
    metric_name: str,
    title: str,
    out_name: str,
    out_dir: Path,
    *,
    scenario: str | None = None,
) -> None:
    metric_groups = _group_by(groups, metric_name, "A", scenario)
    if not metric_groups:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.text(0.5, 0.5, f"No data for {metric_name}", ha="center", va="center")
        ax.set_axis_off()
        _save_fig(fig, out_dir, out_name)
        return
    tiers = _tier_order(sorted({g["tags"].get("memory_tier", "") for g in metric_groups}))
    data: list[list[float]] = [
        list(next((g.get("values") for g in metric_groups if g["tags"].get("memory_tier") == t), []) or [])
        for t in tiers
    ]
    if all(len(set(series)) <= 1 for series in data if series):
        means = [float(series[0]) if series else 0.0 for series in data]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(tiers, means, color="#52796f")
        ax.set_ylabel(metric_name.replace("suite_a.", "").replace("_", " ").title())
        ax.set_title(title)
        ax.set_ylim(0, 1.05)
        _save_fig(fig, out_dir, out_name)
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.violinplot(data, showmeans=True)
    ax.set_xticks(range(1, len(tiers) + 1))
    ax.set_xticklabels(tiers)
    ax.set_ylabel(metric_name.replace("suite_a.", "").replace("_", " ").title())
    ax.set_title(title)
    _save_fig(fig, out_dir, out_name)


def generate_figures(analysis_path: Path, figures_dir: Path) -> None:
    analysis = _load_analysis(analysis_path)
    groups: list[dict[str, Any]] = list(analysis.get("groups", []))
    plot_accuracy_by_tier(groups, figures_dir, scenario="baseline")
    plot_accuracy_by_tier(
        groups,
        figures_dir,
        scenario="adversarial",
        title="Suite A Adversarial Accuracy by Memory Tier",
        out_name="accuracy_by_tier_adversarial",
    )
    plot_latency_summary(groups, figures_dir)
    plot_throughput_errors(groups, figures_dir)
    plot_violin(
        groups,
        "suite_a.drift",
        "Suite A Drift by Memory Tier",
        "drift_violin",
        figures_dir,
        scenario="baseline",
    )
    plot_violin(
        groups,
        "suite_a.faithfulness",
        "Suite A Faithfulness by Memory Tier",
        "faithfulness_violin",
        figures_dir,
        scenario="baseline",
    )
