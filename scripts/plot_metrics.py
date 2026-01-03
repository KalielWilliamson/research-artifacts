#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from src.alphaflow.evals.system_paper.plots import generate_figures


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot system-paper figures from analysis JSON.")
    parser.add_argument(
        "--analysis",
        type=str,
        default="research/papers/event-driven-agentic-memory/output/analysis.json",
        help="Path to analysis JSON.",
    )
    parser.add_argument(
        "--figures-dir",
        type=str,
        default="research/papers/event-driven-agentic-memory/figures",
        help="Directory for figure outputs.",
    )
    args = parser.parse_args()

    generate_figures(Path(args.analysis), Path(args.figures_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
