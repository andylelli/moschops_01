"""
Meta-labeling (de Prado, AFML Ch. 3).

A MetaLabeler wraps a primary binary classifier.  A secondary (meta) model
learns when to act on the primary model's signal, improving precision at the
cost of recall.

The meta-model is trained only on bars where the primary model fires a signal
(primary_prob ≥ threshold).  Its target is whether the primary model was correct
on those bars.

Usage:
    from meta_label import MetaLabeler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier

    primary   = LogisticRegression()
    secondary = RandomForestClassifier(n_estimators=100)
    labeler   = MetaLabeler(primary, secondary, threshold=0.5)
    labeler.fit(X_train, y_train)

    # Filtered probability: P(signal) × P(correct|signal)
    filtered = labeler.filtered_proba(X_test)
"""
from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, clone


class MetaLabeler(BaseEstimator, ClassifierMixin):
    """
    Two-stage classifier that filters primary model signals.

    Parameters
    ----------
    primary   : sklearn-compatible classifier — the signal generator
    secondary : sklearn-compatible classifier — the meta-filter
    threshold : float — primary probability threshold for a "signal" (default 0.5)
    """

    def __init__(self, primary, secondary, threshold: float = 0.5) -> None:
        self.primary = primary
        self.secondary = secondary
        self.threshold = threshold

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MetaLabeler":
        """
        Fit both the primary and secondary models.

        Steps:
        1. Fit primary on all (X, y).
        2. Predict primary labels on training set.
        3. Build meta-labels: 1 = primary was correct, 0 = primary was wrong.
        4. Fit secondary only on bars where primary fired (primary_pred == 1).

        Parameters
        ----------
        X : np.ndarray of shape (n_samples, n_features)
        y : np.ndarray of shape (n_samples,) — binary labels {0, 1}
        """
        X = np.asarray(X)
        y = np.asarray(y)

        self.primary_ = clone(self.primary)
        self.primary_.fit(X, y)

        primary_prob = self.primary_.predict_proba(X)[:, 1]
        primary_pred = (primary_prob >= self.threshold).astype(int)

        # Meta-label: 1 if primary was correct on that bar
        meta_y = (primary_pred == y).astype(int)

        signal_mask = primary_pred == 1
        n_signals = int(signal_mask.sum())

        if n_signals < 10:
            # Too few signals to fit a secondary model; secondary is disabled
            self.secondary_ = None
        else:
            self.secondary_ = clone(self.secondary)
            self.secondary_.fit(X[signal_mask], meta_y[signal_mask])

        self.classes_ = np.array([0, 1])
        self.n_signals_train_ = n_signals
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Return [P(incorrect|signal), P(correct|signal)] for each bar.

        For bars where the primary did not fire, P(correct|signal) = 0.
        """
        X = np.asarray(X)
        primary_prob = self.primary_.predict_proba(X)[:, 1]
        primary_signal = primary_prob >= self.threshold

        meta_prob = np.zeros(len(X))
        if self.secondary_ is not None and primary_signal.any():
            meta_prob[primary_signal] = self.secondary_.predict_proba(
                X[primary_signal]
            )[:, 1]

        return np.column_stack([1.0 - meta_prob, meta_prob])

    def filtered_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Combined signal strength: P(primary_signal) × P(correct | signal).

        Use this scalar as the final confidence score for trade sizing or
        further threshold-based filtering.

        Returns
        -------
        np.ndarray of shape (n_samples,) — values in [0, 1].
        """
        X = np.asarray(X)
        primary_prob = self.primary_.predict_proba(X)[:, 1]
        meta_prob = self.predict_proba(X)[:, 1]
        return primary_prob * meta_prob

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.filtered_proba(X) >= self.threshold).astype(int)
