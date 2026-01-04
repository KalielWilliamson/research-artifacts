#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis_lib import aggregate_metrics, load_metrics


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = sorted({key for row in rows for key in row})
    lines = [",".join(headers)]
    for row in rows:
        line = []
        for key in headers:
            val = row.get(key, "")
            if isinstance(val, float):
                line.append(f"{val:.6f}")
            else:
                line.append(str(val).replace(",", ";"))
        lines.append(",".join(line))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _flatten_groups(groups: list[dict[str, Any]], comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparison_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for comp in comparisons:
        key = (
            comp.get("suite", ""),
            comp.get("metric_name", ""),
            json.dumps(comp.get("compare_tags", {}), sort_keys=True),
        )
        comparison_index[key] = comp

    rows: list[dict[str, Any]] = []
    for group in groups:
        tags = group.get("tags", {})
        row: dict[str, Any] = {
            "suite": group.get("suite", ""),
            "metric_name": group.get("metric_name", ""),
            "memory_tier": tags.get("memory_tier", ""),
            "scenario": tags.get("scenario", ""),
            "n": group.get("n", 0),
            "mean": group.get("mean", 0.0),
            "median": group.get("median", 0.0),
            "std": group.get("std", 0.0),
            "ci_low": group.get("ci_low", 0.0),
            "ci_high": group.get("ci_high", 0.0),
        }
        comp = comparison_index.get(
            (
                row["suite"],
                row["metric_name"],
                json.dumps(tags, sort_keys=True),
            )
        )
        if comp:
            row["cohens_d"] = comp.get("cohens_d")
            row["cliffs_delta"] = comp.get("cliffs_delta")
            row["p_mann_whitney"] = comp.get("p_mann_whitney")
            row["p_ks"] = comp.get("p_ks")
        rows.append(row)
    return rows


def _write_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["suite", "metric", "tier", "scenario", "mean", "ci_low", "ci_high", "cohens_d", "p_mw"]

    def _escape(text: str) -> str:
        return (
            text.replace("\\", "\\textbackslash{}")
            .replace("&", "\\&")
            .replace("%", "\\%")
            .replace("$", "\\$")
            .replace("#", "\\#")
            .replace("_", "\\_")
            .replace("{", "\\{")
            .replace("}", "\\}")
        )

    lines = [
        "\\begin{tabular}{lllllllll}",
        " & ".join(_escape(h) for h in headers) + " \\\\",
        "\\hline",
    ]
    for row in rows:
        values = [
            _escape(str(row.get("suite", ""))),
            _escape(str(row.get("metric_name", ""))),
            _escape(str(row.get("memory_tier", ""))),
            _escape(str(row.get("scenario", ""))),
            f"{row.get('mean', 0.0):.3f}",
            f"{row.get('ci_low', 0.0):.3f}",
            f"{row.get('ci_high', 0.0):.3f}",
            f"{row.get('cohens_d', 0.0):.3f}",
            f"{row.get('p_mann_whitney', 1.0):.3f}",
        ]
        lines.append(" & ".join(values) + " \\\\")
    lines += ["\\hline", "\\end{tabular}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def _find_row(
    rows: list[dict[str, Any]],
    *,
    suite: str,
    metric: str,
    scenario: str,
    tier: str,
) -> dict[str, Any] | None:
    matches = [
        row
        for row in rows
        if row.get("suite") == suite
        and row.get("metric_name") == metric
        and row.get("scenario") == scenario
        and row.get("memory_tier") == tier
    ]
    if not matches:
        return None
    return max(matches, key=lambda row: int(row.get("n", 0)))


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "-"


def _write_summary_anchor(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    anchors = []
    a_no_acc = _find_row(
        rows,
        suite="A",
        metric="suite_a.accuracy",
        scenario="baseline",
        tier="no-memory",
    )
    a_no_drift = _find_row(
        rows,
        suite="A",
        metric="suite_a.drift",
        scenario="baseline",
        tier="no-memory",
    )
    anchors.append(
        {
            "anchor": "A no-memory (baseline)",
            "accuracy": _format_value(a_no_acc.get("mean") if a_no_acc else None),
            "drift": _format_value(a_no_drift.get("mean") if a_no_drift else None),
            "p95": "-",
            "rps": "-",
            "replay": "-",
        }
    )
    a_hybrid_acc = _find_row(
        rows,
        suite="A",
        metric="suite_a.accuracy",
        scenario="baseline",
        tier="hybrid",
    )
    a_hybrid_drift = _find_row(
        rows,
        suite="A",
        metric="suite_a.drift",
        scenario="baseline",
        tier="hybrid",
    )
    anchors.append(
        {
            "anchor": "A hybrid",
            "accuracy": _format_value(a_hybrid_acc.get("mean") if a_hybrid_acc else None),
            "drift": _format_value(a_hybrid_drift.get("mean") if a_hybrid_drift else None),
            "p95": "-",
            "rps": "-",
            "replay": "-",
        }
    )
    b_base_p95 = _find_row(
        rows,
        suite="B",
        metric="load.p95_ms",
        scenario="baseline",
        tier="",
    )
    b_base_rps = _find_row(
        rows,
        suite="B",
        metric="load.rps",
        scenario="baseline",
        tier="",
    )
    anchors.append(
        {
            "anchor": "B baseline",
            "accuracy": "-",
            "drift": "-",
            "p95": _format_value(b_base_p95.get("mean") if b_base_p95 else None),
            "rps": _format_value(b_base_rps.get("mean") if b_base_rps else None),
            "replay": "-",
        }
    )
    b_fault_p95 = _find_row(
        rows,
        suite="B",
        metric="load.p95_ms",
        scenario="fault-heavy",
        tier="",
    )
    b_fault_rps = _find_row(
        rows,
        suite="B",
        metric="load.rps",
        scenario="fault-heavy",
        tier="",
    )
    anchors.append(
        {
            "anchor": "B fault-heavy",
            "accuracy": "-",
            "drift": "-",
            "p95": _format_value(b_fault_p95.get("mean") if b_fault_p95 else None),
            "rps": _format_value(b_fault_rps.get("mean") if b_fault_rps else None),
            "replay": "-",
        }
    )
    c_replay = _find_row(
        rows,
        suite="C",
        metric="completion.hash",
        scenario="",
        tier="",
    )
    replay_text = "-"
    if c_replay:
        n = int(c_replay.get("n", 0))
        mean = float(c_replay.get("mean", 0.0))
        success = int(round(mean * n)) if n else 0
        replay_text = f"{success}/{n} (hash match)" if n else "-"
    anchors.append(
        {
            "anchor": "C replay",
            "accuracy": "-",
            "drift": "-",
            "p95": "-",
            "rps": "-",
            "replay": replay_text,
        }
    )

    def _escape(text: str) -> str:
        return (
            text.replace("\\", "\\textbackslash{}")
            .replace("&", "\\&")
            .replace("%", "\\%")
            .replace("$", "\\$")
            .replace("#", "\\#")
            .replace("_", "\\_")
            .replace("{", "\\{")
            .replace("}", "\\}")
        )

    lines = [
        "\\begin{tabular}{lrrrrl}",
        "anchor & accuracy & drift & p95 latency (ms) & rps & replay success \\\\",
        "\\hline",
    ]
    for row in anchors:
        values = [
            _escape(row["anchor"]),
            _escape(row["accuracy"]),
            _escape(row["drift"]),
            _escape(row["p95"]),
            _escape(row["rps"]),
            _escape(row["replay"]),
        ]
        lines.append(" & ".join(values) + " \\\\")
    lines += ["\\hline", "\\end{tabular}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def load_metrics_from_paths(paths: list[Path]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        for record in load_metrics(path):
            key = json.dumps(record, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            records.append(record)
    return records


def _expand_metrics_paths(values: list[str]) -> list[Path]:
    if not values:
        return []
    paths: list[Path] = []
    for value in values:
        p = Path(value)
        if p.is_dir():
            if p.name == "artifacts":
                paths.extend(sorted(_latest_artifacts(p)))
            else:
                paths.extend(sorted(p.glob("**/metrics.jsonl")))
        elif "*" in value:
            paths.extend(sorted(Path(".").glob(value)))
        else:
            paths.append(p)
    return paths


def _latest_artifacts(root: Path) -> list[Path]:
    metrics_paths: list[Path] = []
    for suite_dir in sorted(root.glob("suite_*")):
        if not suite_dir.is_dir():
            continue
        runs = sorted((run for run in suite_dir.iterdir() if run.is_dir()), key=lambda p: p.name)
        for run in runs:
            metrics_path = run / "metrics.jsonl"
            if metrics_path.exists():
                metrics_paths.append(metrics_path)
    return metrics_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate system-paper metrics into analysis tables.")
    parser.add_argument(
        "--metrics",
        type=str,
        action="append",
        default=[],
        help="Metrics JSONL path or directory (repeatable).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="research/papers/event-driven-agentic-memory/output",
        help="Directory for analysis JSON/CSV.",
    )
    parser.add_argument(
        "--tables-dir",
        type=str,
        default="research/papers/event-driven-agentic-memory/tables",
        help="Directory for tables outputs.",
    )
    args = parser.parse_args()

    metrics_inputs = args.metrics or [
        "research/papers/event-driven-agentic-memory/output/metrics.jsonl",
        "artifacts",
    ]
    output_dir = Path(args.output_dir)
    tables_dir = Path(args.tables_dir)

    metric_paths = _expand_metrics_paths(metrics_inputs)
    if not metric_paths:
        raise SystemExit("No metrics files found for analysis.")
    records = load_metrics_from_paths(metric_paths)
    analysis = aggregate_metrics(records)
    analysis["generated_at"] = datetime.now(timezone.utc).isoformat()
    analysis["source_metrics"] = [str(path) for path in metric_paths]

    _write_json(output_dir / "analysis.json", analysis)
    rows = _flatten_groups(analysis["groups"], analysis["comparisons"])
    _write_csv(output_dir / "analysis.csv", rows)
    _write_csv(tables_dir / "metrics_summary.csv", rows)
    _write_json(tables_dir / "metrics_summary.json", rows)
    _write_tex(tables_dir / "metrics_summary.tex", rows)
    _write_summary_anchor(tables_dir / "summary_anchor.tex", rows)
    print(f"analysis: wrote {output_dir / 'analysis.json'} and tables in {tables_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
