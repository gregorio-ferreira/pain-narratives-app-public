"""Agreement measures between real and synthetic questionnaire scores.

Correlation (Pearson's r) measures association; the functions here measure
agreement, i.e. whether the two sets of scores take the same values. A constant
offset between real and synthetic scores leaves r unchanged but lowers alpha.
"""

from __future__ import annotations

from typing import Callable

import krippendorff
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
    keep = ~(np.isnan(a) | np.isnan(b))
    return float(krippendorff.alpha(reliability_data=np.vstack([a[keep], b[keep]]), level_of_measurement="interval"))


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
