"""
Cross-validation splitters for time-series walk-forward training.

Provides:
- ExpandingWindowCV  — sklearn-compatible splitter with anchored start and
  expanding training set (alternative to sklearn's TimeSeriesSplit which
  uses a fixed training-window size).

Usage:
    from cv import ExpandingWindowCV
    cv = ExpandingWindowCV(n_splits=5, min_train=200)
    for train_idx, test_idx in cv.split(X):
        model.fit(X[train_idx], y[train_idx])
        ...

    # With sklearn cross_validate:
    from sklearn.model_selection import cross_validate
    results = cross_validate(estimator, X, y, cv=cv)
"""
from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator


class ExpandingWindowCV(BaseEstimator):
    """
    Expanding (anchored-start) walk-forward cross-validation splitter.

    The training set always begins at bar 0 and grows by one fold width
    per split.  The test set immediately follows the training set and is
    fixed-width.

    This differs from sklearn's TimeSeriesSplit (rolling window) in that
    the model always sees all historical data up to each test fold.

    Parameters
    ----------
    n_splits  : int — number of train/test folds (≥ 2)
    min_train : int — minimum number of bars in the first training set
    """

    def __init__(self, n_splits: int = 5, min_train: int = 200) -> None:
        if n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        if min_train < 1:
            raise ValueError("min_train must be >= 1")
        self.n_splits = n_splits
        self.min_train = min_train

    # noinspection PyUnusedLocal
    def split(self, X, y=None, groups=None):  # noqa: N803 (sklearn API)
        """
        Yield (train_indices, test_indices) for each fold.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)

        Yields
        ------
        train : np.ndarray — indices [0, train_end)
        test  : np.ndarray — indices [train_end, test_end)
        """
        n = len(X)
        total_test = n - self.min_train
        if total_test < self.n_splits:
            raise ValueError(
                f"Insufficient data: need at least {self.min_train + self.n_splits} bars, "
                f"got {n}.  Reduce min_train or n_splits."
            )

        fold_size = total_test // self.n_splits

        for i in range(self.n_splits):
            train_end = self.min_train + i * fold_size
            test_start = train_end
            test_end = test_start + fold_size if i < self.n_splits - 1 else n
            yield np.arange(0, train_end), np.arange(test_start, test_end)

    def get_n_splits(self, X=None, y=None, groups=None) -> int:  # noqa: N803
        return self.n_splits
