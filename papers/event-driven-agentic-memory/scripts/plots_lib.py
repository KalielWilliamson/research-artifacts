from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import numpy as np


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


def _find_group(
    groups: list[dict[str, Any]],
    *,
    suite: str,
    metric: str,
    scenario: str | None = None,
    tier: str | None = None,
) -> dict[str, Any] | None:
    for g in groups:
        if g.get("suite") != suite or g.get("metric_name") != metric:
            continue
        tags = g.get("tags", {})
        if scenario is not None and tags.get("scenario", "") != scenario:
            continue
        if tier is not None and tags.get("memory_tier", "") != tier:
            continue
        return g
    return None


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
    p50_groups = _group_by(groups, "load.p50_ms", "B")
    p95_groups = _group_by(groups, "load.p95_ms", "B")
    if not avg_groups or not p50_groups or not p95_groups:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.text(0.5, 0.5, "No Suite B latency data", ha="center", va="center")
        ax.set_axis_off()
        _save_fig(fig, out_dir, "latency_summary")
        return
    scenario_order = ["baseline", "fault-light", "fault-heavy"]
    scenarios = [s for s in scenario_order if any(g["tags"].get("scenario") == s for g in p95_groups)]
    if not scenarios:
        scenarios = sorted({g["tags"].get("scenario", "") for g in p95_groups})

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    palette = {"baseline": "#1d4ed8", "fault-light": "#0f766e", "fault-heavy": "#b91c1c"}
    percentile_x = np.array([50.0, 95.0], dtype=float)

    for scenario in scenarios:
        p50 = next((g for g in p50_groups if g["tags"].get("scenario") == scenario), None)
        p95 = next((g for g in p95_groups if g["tags"].get("scenario") == scenario), None)
        if p50 is None or p95 is None:
            continue
        y = np.array([float(p50.get("mean", 0.0)), float(p95.get("mean", 0.0))], dtype=float)
        color = palette.get(scenario, "#334155")
        ax.plot(percentile_x, y, marker="o", linewidth=2.0, markersize=6, color=color, label=scenario)

    ax.set_xlabel("Percentile")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Suite B Latency Percentile Curves")
    ax.set_xlim(48, 97)
    ax.grid(alpha=0.2, linestyle="--")
    ax.legend(frameon=False, fontsize=8)

    inset = inset_axes(ax, width="40%", height="40%", loc="upper right", borderpad=1.0)
    for scenario in scenarios:
        g = next((x for x in p95_groups if x["tags"].get("scenario") == scenario), None)
        if g is None:
            continue
        values = sorted(float(v) for v in (g.get("values") or []))
        if not values:
            continue
        y = np.arange(1, len(values) + 1, dtype=float) / float(len(values))
        inset.step(values, y, where="post", linewidth=1.2, color=palette.get(scenario, "#334155"))
    inset.set_title("ECDF (p95/run)", fontsize=7)
    inset.tick_params(axis="both", labelsize=6)
    inset.grid(alpha=0.15, linestyle=":")

    _save_fig(fig, out_dir, "latency_summary")


def plot_rq1_quality_tradeoff(groups: list[dict[str, Any]], out_dir: Path) -> None:
    acc_groups = _group_by(groups, "suite_a.accuracy", "A", "baseline")
    drift_groups = _group_by(groups, "suite_a.drift", "A", "baseline")
    if not acc_groups or not drift_groups:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.text(0.5, 0.5, "No Suite A baseline tradeoff data", ha="center", va="center")
        ax.set_axis_off()
        _save_fig(fig, out_dir, "rq1_quality_tradeoff")
        return

    tiers = _tier_order(sorted({g.get("tags", {}).get("memory_tier", "") for g in acc_groups}))
    points: list[tuple[str, float, float]] = []
    for tier in tiers:
        acc = _find_group(groups, suite="A", metric="suite_a.accuracy", scenario="baseline", tier=tier)
        drift = _find_group(groups, suite="A", metric="suite_a.drift", scenario="baseline", tier=tier)
        if acc is None or drift is None:
            continue
        points.append((tier, float(drift.get("mean", 0.0)), float(acc.get("mean", 0.0))))

    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = {
        "no-memory": "#9ca3af",
        "summary": "#38bdf8",
        "vector": "#10b981",
        "graph": "#14b8a6",
        "hybrid": "#065f46",
    }
    for tier, x_drift, y_acc in points:
        ax.scatter(x_drift, y_acc, s=140, color=colors.get(tier, "#334155"), edgecolor="white", linewidth=1.0)
        ax.annotate(tier, (x_drift, y_acc), xytext=(6, 4), textcoords="offset points", fontsize=8)

    ax.set_xlabel("Drift (lower is better)")
    ax.set_ylabel("Accuracy")
    ax.set_title("RQ1 Quality Tradeoff by Hierarchical Memory/State Tier")
    ax.set_xlim(left=-0.02, right=max(1.02, max((p[1] for p in points), default=1.0) + 0.05))
    ax.set_ylim(0.0, 1.05)
    ax.grid(alpha=0.2, linestyle="--")
    _save_fig(fig, out_dir, "rq1_quality_tradeoff")


def plot_rq2_reliability_frontier(groups: list[dict[str, Any]], out_dir: Path) -> None:
    scenarios = ["baseline", "fault-light", "fault-heavy"]
    rows: list[tuple[str, float, float]] = []
    for s in scenarios:
        p95 = _find_group(groups, suite="B", metric="load.p95_ms", scenario=s)
        errs = _find_group(groups, suite="B", metric="load.errors", scenario=s)
        reqs = _find_group(groups, suite="B", metric="load.requests", scenario=s)
        if p95 is None or errs is None or reqs is None:
            continue
        req_mean = float(reqs.get("mean", 0.0))
        err_rate = float(errs.get("mean", 0.0)) / req_mean if req_mean else 0.0
        rows.append((s, err_rate, float(p95.get("mean", 0.0))))

    if not rows:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.text(0.5, 0.5, "No Suite B reliability frontier data", ha="center", va="center")
        ax.set_axis_off()
        _save_fig(fig, out_dir, "rq2_reliability_frontier")
        return

    fig, ax = plt.subplots(figsize=(7, 4.5))
    palette = {"baseline": "#2563eb", "fault-light": "#16a34a", "fault-heavy": "#dc2626"}
    for s, err_rate, p95 in rows:
        ax.scatter(err_rate * 100.0, p95, s=160, color=palette.get(s, "#334155"), edgecolor="white", linewidth=1.2)
        ax.annotate(s, (err_rate * 100.0, p95), xytext=(6, 4), textcoords="offset points", fontsize=8)

    if len(rows) >= 2:
        xs = [r[1] * 100.0 for r in rows]
        ys = [r[2] for r in rows]
        order = np.argsort(xs)
        ax.plot(np.array(xs)[order], np.array(ys)[order], color="#64748b", linewidth=1.2, alpha=0.8)

    ax.set_xlabel("Error rate (%)")
    ax.set_ylabel("p95 latency (ms)")
    ax.set_title("RQ2 Reliability Frontier Under Injected Failures")
    ax.grid(alpha=0.2, linestyle="--")
    _save_fig(fig, out_dir, "rq2_reliability_frontier")


def plot_rq3_replay_consistency(groups: list[dict[str, Any]], out_dir: Path) -> None:
    rows = [g for g in groups if g.get("suite") == "C" and g.get("metric_name") == "completion.hash"]
    buckets: dict[str, tuple[float, int]] = {"stubbed": (0.0, 0), "auto": (0.0, 0)}
    for g in rows:
        tags = g.get("tags", {})
        mode = "auto"
        hash_tag = str(tags.get("hash", ""))
        if hash_tag.startswith("[stub]"):
            mode = "stubbed"
        elif str(tags.get("llm_mode", "")).strip().lower() == "stub":
            mode = "stubbed"
        mean = float(g.get("mean", 0.0))
        n = int(g.get("n", 0))
        prev_mean, prev_n = buckets[mode]
        total_n = prev_n + n
        if total_n == 0:
            continue
        weighted = ((prev_mean * prev_n) + (mean * n)) / total_n
        buckets[mode] = (weighted, total_n)

    labels = [k for k, (_, n) in buckets.items() if n > 0]
    if not labels:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        ax.text(0.5, 0.5, "No Suite C replay consistency data", ha="center", va="center")
        ax.set_axis_off()
        _save_fig(fig, out_dir, "rq3_replay_consistency")
        return

    vals = [buckets[k][0] for k in labels]
    ns = [buckets[k][1] for k in labels]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.bar(labels, vals, color=["#0ea5e9", "#0284c7"])
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("Replay pass rate")
    ax.set_title("RQ3 Replay Consistency by Evaluation Mode")
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    for bar, n in zip(bars, ns, strict=False):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, f"n={n}", ha="center", fontsize=8)
    _save_fig(fig, out_dir, "rq3_replay_consistency")


def plot_graceful_degradation_profile(groups: list[dict[str, Any]], out_dir: Path) -> None:
    rows = [g for g in groups if g.get("metric_name") == "degradation.useful_count"]
    if not rows:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        ax.text(0.5, 0.5, "No graceful degradation data", ha="center", va="center")
        ax.set_axis_off()
        _save_fig(fig, out_dir, "graceful_degradation_profile")
        return
    labels = []
    vals = []
    for g in sorted(rows, key=lambda x: str(x.get("tags", {}).get("case", ""))):
        tags = g.get("tags", {})
        labels.append(f"{tags.get('case','?')}:{tags.get('scenario','')}")
        vals.append(float(g.get("mean", 0.0)))
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.bar(labels, vals, color=["#94a3b8", "#16a34a", "#ef4444"][: len(vals)])
    ax.set_ylabel("Useful outputs (mean)")
    ax.set_title("Graceful Degradation Output Profile")
    ax.tick_params(axis="x", labelrotation=12)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    _save_fig(fig, out_dir, "graceful_degradation_profile")


def plot_event_traceability_map(out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 3.8))
    ax.set_axis_off()
    boxes = {
        "gateway": (0.04, 0.56, 0.16, 0.24, "Gateway"),
        "bus": (0.25, 0.56, 0.16, 0.24, "Event Bus"),
        "bridge": (0.46, 0.56, 0.18, 0.24, "Cognition Bridge"),
        "memory": (0.69, 0.68, 0.22, 0.14, "Hierarchical Memory/State"),
        "output": (0.69, 0.44, 0.22, 0.14, "Agent Output"),
        "trace": (0.25, 0.18, 0.39, 0.20, "Replay/Trace Store"),
    }
    for key, (x, y, w, h, label) in boxes.items():
        color = "#dbeafe" if key in {"gateway", "bus", "bridge"} else "#dcfce7"
        rect = plt.Rectangle((x, y), w, h, facecolor=color, edgecolor="#334155", linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9)

    arrows = [
        ((0.20, 0.68), (0.25, 0.68)),
        ((0.41, 0.68), (0.46, 0.68)),
        ((0.64, 0.74), (0.69, 0.75)),
        ((0.64, 0.60), (0.69, 0.51)),
        ((0.33, 0.56), (0.33, 0.38)),
        ((0.55, 0.56), (0.55, 0.38)),
    ]
    for (x1, y1), (x2, y2) in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.2, color="#334155"))

    ax.text(0.08, 0.36, "Capture points:", fontsize=8.5, fontweight="bold")
    ax.text(0.08, 0.31, "L95, q_to, q_err, u, E_replay", fontsize=8.5, color="#0f172a")
    ax.text(0.25, 0.05, "Event-structured flow with explicit traceability and replay criteria", fontsize=8.5)
    _save_fig(fig, out_dir, "event_traceability_map")


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
    plot_event_traceability_map(figures_dir)
    plot_rq1_quality_tradeoff(groups, figures_dir)
    plot_rq2_reliability_frontier(groups, figures_dir)
    plot_rq3_replay_consistency(groups, figures_dir)
    plot_graceful_degradation_profile(groups, figures_dir)
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
