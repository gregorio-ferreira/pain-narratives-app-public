import numpy as np
import pytest

from pain_narratives.analysis.agreement import bootstrap_ci, krippendorff_alpha_interval


def _alpha_closed_form(a, b):
    # Two coders, no missing data: alpha = 1 - D_o / D_e with the interval metric.
    v = np.concatenate([a, b])
    d_o = np.sum((a - b) ** 2) / len(a)
    d_e = 2 * np.sum((v - v.mean()) ** 2) / (len(v) - 1)
    return 1 - d_o / d_e


def test_identical_scores_give_alpha_one():
    a = np.array([10.0, 20.0, 31.0, 44.0, 52.0])
    assert krippendorff_alpha_interval(a, a.copy()) == pytest.approx(1.0)


def test_matches_closed_form():
    rng = np.random.default_rng(0)
    a = rng.normal(30, 10, size=150)
    b = a + rng.normal(3, 8, size=150)
    assert krippendorff_alpha_interval(a, b) == pytest.approx(_alpha_closed_form(a, b))


def test_offset_lowers_alpha_but_not_correlation():
    rng = np.random.default_rng(1)
    a = rng.normal(30, 10, size=150)
    shifted = a + 10
    assert np.corrcoef(a, shifted)[0, 1] == pytest.approx(1.0)
    assert krippendorff_alpha_interval(a, shifted) < 0.8


def test_missing_pairs_are_dropped():
    a = np.array([1.0, 2.0, 3.0, np.nan, 5.0])
    b = np.array([1.0, 2.0, 3.0, 4.0, np.nan])
    assert krippendorff_alpha_interval(a, b) == pytest.approx(1.0)


def test_bootstrap_ci_is_reproducible_and_brackets_estimate():
    rng = np.random.default_rng(2)
    a = rng.normal(30, 10, size=150)
    b = a + rng.normal(3, 8, size=150)
    first = bootstrap_ci(krippendorff_alpha_interval, a, b, iters=500)
    second = bootstrap_ci(krippendorff_alpha_interval, a, b, iters=500)
    assert first == second
    assert first[0] < krippendorff_alpha_interval(a, b) < first[1]
