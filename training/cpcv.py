"""
Combinatorial Purged Cross-Validation (CPCV) and
Probability of Backtest Overfitting (PBO).

CPCV: de Prado (2018), AFML Ch. 12.
PBO:  Bailey et al. (2014), "The Probability of Backtest Overfitting".

CPCV splits the time series into T groups and runs C(T, k) train/test
combinations (testing on k groups at a time), yielding far more out-of-sample
paths than standard walk-forward.  Embargo gaps prevent lookahead bias.

PBO uses the CPCV OOS Sharpe ratios to estimate the probability that the
selected (IS-optimal) strategy is overfit to the training data.

Usage:
    from cpcv import CombPurgedCV, probability_of_backtest_overfitting

    cv = CombPurgedCV(n_groups=6, n_test_groups=2, embargo_pct=0.01)
    for train_idx, test_idx in cv.split(X):
        model.fit(X[train_idx], y[train_idx])
        ...

    # PBO from a matrix of OOS Sharpe ratios:
    # rows = CPCV paths, cols = strategy variants (or hyperparameter configs)
    pbo = probability_of_backtest_overfitting(sharpe_matrix)
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from sklearn.base import BaseEstimator


class CombPurgedCV(BaseEstimator):
    """
    Combinatorial Purged Cross-Validation splitter.

    The dataset is divided into n_groups equal-sized blocks.  For each
    combination of n_test_groups blocks, those blocks form the test set and
    the remaining blocks form the training set.  A per-block embargo gap is
    removed from each end of the training set adjacent to a test block.

    Parameters
    ----------
    n_groups      : int   — number of equal-sized blocks (T)
    n_test_groups : int   — blocks per test set (k);  C(T,k) total paths
    embargo_pct   : float — fraction of a group width to embargo at each boundary
    """

    def __init__(
        self,
        n_groups: int = 6,
        n_test_groups: int = 2,
        embargo_pct: float = 0.01,
    ) -> None:
        if n_groups < 3:
            raise ValueError("n_groups must be >= 3")
        if n_test_groups < 1 or n_test_groups >= n_groups:
            raise ValueError("n_test_groups must be in [1, n_groups)")
        self.n_groups = n_groups
        self.n_test_groups = n_test_groups
        self.embargo_pct = embargo_pct

    def split(self, X, y=None, groups=None):  # noqa: N803
        """
        Yield (train_indices, test_indices) for each CPCV combination.

        Yields
        ------
        train : np.ndarray of int indices (embargo regions removed)
        test  : np.ndarray of int indices
        """
        n = len(X)
        group_size = n // self.n_groups
        embargo = max(1, int(group_size * self.embargo_pct))

        # Group boundaries [start, end)
        boundaries = [
            (i * group_size, (i + 1) * group_size if i < self.n_groups - 1 else n)
            for i in range(self.n_groups)
        ]

        for test_groups in itertools.combinations(range(self.n_groups), self.n_test_groups):
            test_set = set(test_groups)
            test_idx = np.concatenate([
                np.arange(boundaries[g][0], boundaries[g][1]) for g in test_groups
            ])

            # Build train indices with embargo removed around each test-group boundary
            train_idx_parts: list[np.ndarray] = []
            for g in range(self.n_groups):
                if g in test_set:
                    continue
                start, end = boundaries[g]

                # Check adjacency to a test block and apply embargo
                adj_left = (g - 1) in test_set
                adj_right = (g + 1) in test_set

                train_start = start + embargo if adj_left else start
                train_end = end - embargo if adj_right else end

                if train_end > train_start:
                    train_idx_parts.append(np.arange(train_start, train_end))

            if train_idx_parts:
                train_idx = np.concatenate(train_idx_parts)
                yield np.sort(train_idx), np.sort(test_idx)

    def get_n_splits(self, X=None, y=None, groups=None) -> int:  # noqa: N803
        return math.comb(self.n_groups, self.n_test_groups)


def probability_of_backtest_overfitting(
    sharpe_matrix: np.ndarray,
    n_bins: int | None = None,
) -> float:
    """
    Estimate the Probability of Backtest Overfitting (PBO).

    Based on Bailey et al. (2014).  The idea: for each CPCV path, rank the
    strategy variants by their in-sample vs. out-of-sample Sharpe.  PBO is
    the fraction of paths where the IS-best variant ranks below the median OOS.

    Parameters
    ----------
    sharpe_matrix : np.ndarray of shape (n_paths, n_strategies)
                    OOS Sharpe ratios for each (path, strategy) combination.
                    Rows = CPCV test paths, Cols = strategy/hyperparameter variants.
    n_bins        : int | None — bins for logit distribution histogram (unused in
                    this implementation; kept for API compatibility)

    Returns
    -------
    float PBO in [0, 1].
    Higher → more likely that the selected strategy is overfit.

    Notes
    -----
    For the single-strategy case (1 column), PBO is computed as the fraction
    of paths where the OOS Sharpe is below 0 (negative OOS performance).
    """
    sharpe_matrix = np.asarray(sharpe_matrix, dtype=float)

    if sharpe_matrix.ndim == 1:
        sharpe_matrix = sharpe_matrix.reshape(-1, 1)

    n_paths, n_strategies = sharpe_matrix.shape

    if n_strategies == 1:
        # Single strategy: PBO = fraction of OOS paths with negative Sharpe
        return float(np.mean(sharpe_matrix[:, 0] < 0))

    # Multi-strategy: for each path, find IS-best strategy, check if OOS below median
    # We use mean of ALL other paths as the IS estimate for each left-out path
    pbo_count = 0

    for p in range(n_paths):
        is_sharpes = np.mean(
            np.delete(sharpe_matrix, p, axis=0), axis=0
        )  # IS: mean across all other paths
        best_is_strategy = int(np.argmax(is_sharpes))
        oos_sharpe_of_best = sharpe_matrix[p, best_is_strategy]
        median_oos = float(np.median(sharpe_matrix[p, :]))
        if oos_sharpe_of_best < median_oos:
            pbo_count += 1

    return float(pbo_count / n_paths) if n_paths > 0 else 0.0
