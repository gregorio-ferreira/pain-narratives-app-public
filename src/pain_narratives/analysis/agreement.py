"""Agreement measures between real and synthetic questionnaire scores.

Correlation (Pearson's r) measures association; the functions here measure
agreement, i.e. whether the two sets of scores take the same values. A constant
offset between real and synthetic scores leaves r unchanged but lowers alpha.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

DEFAULT_BOOTSTRAP_ITERS = 2000
DEFAULT_SEED = 42


def krippendorff_alpha_interval(a: np.ndarray, b: np.ndarray) -> float:
    """Krippendorff's alpha (interval metric) for two paired score vectors.

    Each position is one unit (participant) rated by two "coders" (real and
    synthetic). Pairs with a missing value on either side are dropped.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.ndim != 1 or b.ndim != 1 or a.shape != b.shape:
        raise ValueError("Agreement requires paired one-dimensional vectors")
    keep = ~(np.isnan(a) | np.isnan(b))
    a, b = a[keep], b[keep]
    if len(a) < 2 or not (np.isfinite(a).all() and np.isfinite(b).all()):
        raise ValueError("Agreement requires at least two finite pairs")
    # Exact interval-alpha formula for two coders with complete paired units.
    # Avoid allocating coincidence/distance matrices on every bootstrap draw.
    pooled = np.concatenate((a, b))
    observed = float(np.mean((a - b) ** 2))
    expected = float(2 * np.sum((pooled - pooled.mean()) ** 2) / (len(pooled) - 1))
    if expected == 0:
        raise ValueError("Interval alpha is undefined for constant pooled scores")
    return 1.0 - observed / expected


def bootstrap_ci(
    stat: Callable[[np.ndarray, np.ndarray], float],
    a: np.ndarray,
    b: np.ndarray,
    iters: int = DEFAULT_BOOTSTRAP_ITERS,
    seed: int = DEFAULT_SEED,
    level: float = 0.95,
) -> tuple[float, float]:
    """Percentile bootstrap CI of a paired statistic, resampling units with replacement.

    Each call uses its own seeded generator, so results do not depend on call order.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(iters, len(a)))
    values = np.array([stat(a[i], b[i]) for i in idx])
    tail = (1 - level) / 2
    lo, hi = np.quantile(values, [tail, 1 - tail])
    return float(lo), float(hi)
