from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable, Iterable
from typing import TypeAlias, cast

import numpy as np
from numpy.typing import NDArray

try:  # pragma: no cover - optional dependency in some environments
    from scipy import stats as _stats  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - fallback when scipy not present
    _stats = None


@dataclass(frozen=True)
class TestResult:
    stat: float | None
    p_value: float | None


FloatArray: TypeAlias = NDArray[np.float64]


def _to_array(values: Iterable[float]) -> FloatArray:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return cast(FloatArray, np.asarray([], dtype=float))
    return cast(FloatArray, arr)


def _mean(arr: FloatArray) -> float:
    return float(np.mean(arr))


def _median(arr: FloatArray) -> float:
    return float(np.median(arr))


def mean(values: Iterable[float]) -> float:
    arr = _to_array(values)
    if arr.size == 0:
        return 0.0
    return float(np.mean(arr))


def median(values: Iterable[float]) -> float:
    arr = _to_array(values)
    if arr.size == 0:
        return 0.0
    return float(np.median(arr))


def std(values: Iterable[float]) -> float:
    arr = _to_array(values)
    if arr.size < 2:
        return 0.0
    return float(np.std(arr, ddof=1))


def bootstrap_ci(
    values: Iterable[float],
    *,
    stat: str = "mean",
    n_samples: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    arr = _to_array(values)
    if arr.size == 0:
        return 0.0, 0.0
    if arr.size == 1:
        return float(arr[0]), float(arr[0])
    rng = np.random.default_rng(seed)
    stat_fn: Callable[[FloatArray], float]
    if stat == "median":
        stat_fn = _median
    else:
        stat_fn = _mean
    boot = rng.choice(arr, size=(n_samples, arr.size), replace=True)
    stats = cast(FloatArray, np.apply_along_axis(stat_fn, 1, boot))
    alpha = (1.0 - ci) / 2.0
    low = np.quantile(stats, alpha)
    high = np.quantile(stats, 1.0 - alpha)
    return float(low), float(high)


def cohens_d(a: Iterable[float], b: Iterable[float]) -> float:
    arr_a = _to_array(a)
    arr_b = _to_array(b)
    if arr_a.size < 2 or arr_b.size < 2:
        return 0.0
    mean_a = np.mean(arr_a)
    mean_b = np.mean(arr_b)
    var_a = np.var(arr_a, ddof=1)
    var_b = np.var(arr_b, ddof=1)
    pooled = ((arr_a.size - 1) * var_a + (arr_b.size - 1) * var_b) / (arr_a.size + arr_b.size - 2)
    if pooled <= 0:
        return 0.0
    return float((mean_a - mean_b) / np.sqrt(pooled))


def cliffs_delta(a: Iterable[float], b: Iterable[float]) -> float:
    arr_a = _to_array(a)
    arr_b = _to_array(b)
    if arr_a.size == 0 or arr_b.size == 0:
        return 0.0
    sorted_b = np.sort(arr_b)
    wins = 0
    losses = 0
    for value in arr_a:
        wins += int(np.searchsorted(sorted_b, value, side="left"))
        losses += int(sorted_b.size - np.searchsorted(sorted_b, value, side="right"))
    total = arr_a.size * arr_b.size
    return float((wins - losses) / total) if total else 0.0


def mann_whitney_u(a: Iterable[float], b: Iterable[float]) -> TestResult:
    if _stats is None:
        return TestResult(stat=None, p_value=None)
    arr_a = _to_array(a)
    arr_b = _to_array(b)
    if arr_a.size == 0 or arr_b.size == 0:
        return TestResult(stat=None, p_value=None)
    res = _stats.mannwhitneyu(arr_a, arr_b, alternative="two-sided")
    return TestResult(stat=float(res.statistic), p_value=float(res.pvalue))


def ks_test(a: Iterable[float], b: Iterable[float]) -> TestResult:
    if _stats is None:
        return TestResult(stat=None, p_value=None)
    arr_a = _to_array(a)
    arr_b = _to_array(b)
    if arr_a.size == 0 or arr_b.size == 0:
        return TestResult(stat=None, p_value=None)
    res = _stats.ks_2samp(arr_a, arr_b)
    return TestResult(stat=float(res.statistic), p_value=float(res.pvalue))
