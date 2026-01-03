from __future__ import annotations

from pathlib import Path
import re


PLACEHOLDERS = {
    "<!--FIGURE:accuracy_by_tier-->": "![](figures/accuracy_by_tier.png)",
    "<!--FIGURE:accuracy_by_tier_adversarial-->": "![](figures/accuracy_by_tier_adversarial.png)",
    "<!--FIGURE:latency_summary-->": "![](figures/latency_summary.png)",
    "<!--FIGURE:throughput_errors-->": "![](figures/throughput_errors.png)",
    "<!--FIGURE:drift_violin-->": "![](figures/drift_violin.png)",
    "<!--FIGURE:faithfulness_violin-->": "![](figures/faithfulness_violin.png)",
    "<!--TABLE:metrics_summary-->": "TABLE:metrics_summary",
    "<!--TABLE:ablation_suite_a-->": "TABLE:ablation_suite_a",
    "<!--TABLE:summary_anchor-->": "TABLE:summary_anchor",
}


def embed_results(results_path: Path) -> None:
    text = results_path.read_text(encoding="utf-8")
    table_path = results_path.parent / "tables" / "metrics_summary.tex"
    table_text = table_path.read_text(encoding="utf-8") if table_path.exists() else ""
    ablation_path = results_path.parent / "output" / "stats" / "table_a_ablation.tex"
    ablation_text = ablation_path.read_text(encoding="utf-8") if ablation_path.exists() else ""
    summary_path = results_path.parent / "tables" / "summary_anchor.tex"
    summary_text = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
    table_text = _wrap_table(table_text)
    ablation_text = _wrap_table(ablation_text)
    summary_text = _wrap_table(summary_text)
    for placeholder, replacement in PLACEHOLDERS.items():
        if placeholder in text:
            if replacement.startswith("TABLE:"):
                if replacement == "TABLE:metrics_summary":
                    text = text.replace(placeholder, table_text)
                elif replacement == "TABLE:ablation_suite_a":
                    text = text.replace(placeholder, ablation_text)
                elif replacement == "TABLE:summary_anchor":
                    text = text.replace(placeholder, summary_text)
            else:
                text = text.replace(placeholder, replacement)
    if "\\input{tables/metrics_summary.tex}" in text:
        text = text.replace("\\input{tables/metrics_summary.tex}", table_text)
    if table_text and "<!--TABLE:metrics_summary-->" in text:
        text = text.replace("<!--TABLE:metrics_summary-->", table_text.strip())
    text = _wrap_raw_tabulars(text)
    results_path.write_text(text, encoding="utf-8")


def _wrap_table(table_text: str) -> str:
    raw = table_text.strip()
    if not raw:
        return table_text
    if "\\begin{tabular}" not in raw:
        return table_text
    if "\\begin{table}" in raw:
        return table_text
    return (
        "\\begin{table}[H]\n"
        "\\centering\n"
        "\\small\n"
        "\\resizebox{\\linewidth}{!}{%\n"
        f"{raw}\n"
        "}\n"
        "\\end{table}\n"
    )


_TABULAR_RE = re.compile(r"(\\begin\{tabular\}.*?\\end\{tabular\})", re.DOTALL)


def _wrap_raw_tabulars(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        tabular = match.group(1).strip()
        prefix = text[: match.start()]
        in_table = prefix.rfind("\\begin{table") > prefix.rfind("\\end{table}")
        if in_table or "\\resizebox{\\linewidth}{!}{" in tabular:
            return match.group(1)
        return (
            "\\begin{table}[H]\n"
            "\\centering\n"
            "\\small\n"
            "\\resizebox{\\linewidth}{!}{%\n"
            f"{tabular}\n"
            "}\n"
            "\\end{table}"
        )

    return _TABULAR_RE.sub(_replace, text)
