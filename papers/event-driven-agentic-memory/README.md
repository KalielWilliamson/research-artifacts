# Artifact Bundle

This bundle provides the data and scripts needed to regenerate the figures and tables
reported in the paper "Event-Driven Agentic Memory: Observable, Replayable Agent
Architectures" without requiring the full platform stack.

## Contents
- output/ : metrics and derived analysis artifacts (CSV/JSON/TeX)
- figures/ : generated plots used in the paper
- scripts/ : analysis and plotting scripts

## Regenerate analysis artifacts
This bundle includes precomputed analysis outputs. To regenerate them, use:

```
python scripts/analyze_metrics.py \
  --analysis output/analysis.json
python scripts/plot_metrics.py \
  --analysis output/analysis.json \
  --figures-dir figures
```

These scripts are self-contained and can be run from the bundle root:

```
python scripts/analyze_metrics.py --analysis output/analysis.json
python scripts/plot_metrics.py --analysis output/analysis.json --figures-dir figures
```

## Notes
- In the public artifacts repository, this bundle lives under `papers/event-driven-agentic-memory/`.
- The bundle intentionally excludes the full platform runtime and service stack.
- If you need end-to-end reproduction, contact the author for a private artifact.
