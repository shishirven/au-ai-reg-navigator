"""Small, dependency-free statistics: bootstrap CIs and Cohen's kappa."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from typing import TypeVar

import numpy as np

T = TypeVar("T")


def mean_or_none(values: Sequence[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return float(np.mean(vals)) if vals else None


def bootstrap_ci(
    items: Sequence[T],
    statistic: Callable[[Sequence[T]], float | None],
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float | None, float | None, float | None]:
    """Percentile bootstrap over items (questions). Returns (point, lo, hi)."""
    point = statistic(items)
    if point is None or len(items) < 2:
        return point, None, None
    rng = np.random.default_rng(seed)
    idx = np.arange(len(items))
    stats = []
    for _ in range(n_boot):
        s = statistic([items[i] for i in rng.choice(idx, size=len(items), replace=True)])
        if s is not None:
            stats.append(s)
    if not stats:
        return point, None, None
    lo, hi = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, float(lo), float(hi)


def cohens_kappa(a: Sequence, b: Sequence, weights: str | None = None) -> float:
    """Cohen's kappa for two raters. ``weights='quadratic'`` for ordinal labels (numeric)."""
    if len(a) != len(b) or not a:
        raise ValueError("need two equal-length, non-empty label lists")
    cats = sorted(set(a) | set(b))
    k = len(cats)
    if k == 1:
        return 1.0
    pos = {c: i for i, c in enumerate(cats)}
    obs = np.zeros((k, k))
    for x, y in zip(a, b, strict=True):
        obs[pos[x], pos[y]] += 1
    obs /= obs.sum()
    exp = np.outer(obs.sum(axis=1), obs.sum(axis=0))
    if weights == "quadratic":
        vals = np.array(cats, dtype=float)
        w = (vals[:, None] - vals[None, :]) ** 2
        w /= w.max() if w.max() else 1
    else:
        w = 1 - np.eye(k)
    denom = (w * exp).sum()
    return float(1 - (w * obs).sum() / denom) if denom else 1.0


def percentile(values: Sequence[float], q: float) -> float | None:
    return float(np.percentile(values, q)) if values else None


def counts(values: Sequence[str]) -> dict[str, int]:
    return dict(Counter(values))
