"""
Soft voting ensemble: LogisticRegression + XGBoost + RandomForest.

XGBoost is lazy-imported; if unavailable the ensemble falls back to
LogisticRegression + RandomForest only.

Usage:
    from ensemble import build_soft_voting_ensemble
    model = build_soft_voting_ensemble(enable_class_weights=True)
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]
"""
from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def build_soft_voting_ensemble(
    enable_class_weights: bool = True,
    n_estimators: int = 200,
    random_state: int = 42,
    lr_max_iter: int = 200,
) -> VotingClassifier:
    """
    Build a soft-voting ensemble of LogisticRegression + XGBoost + RandomForest.

    The estimators are equally weighted (weights=None → uniform).
    XGBoost is included when xgboost is installed; omitted otherwise so the
    ensemble remains functional in minimal environments.

    Parameters
    ----------
    enable_class_weights : bool — pass class-weight hints to each estimator
    n_estimators         : int  — number of trees for RF and XGBoost
    random_state         : int  — reproducibility seed for all estimators
    lr_max_iter          : int  — LogisticRegression max_iter

    Returns
    -------
    sklearn VotingClassifier (voting='soft') ready to call .fit()/.predict_proba()
    """
    cw_lr = "balanced" if enable_class_weights else None
    cw_rf = "balanced_subsample" if enable_class_weights else None

    logreg_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            max_iter=lr_max_iter,
            class_weight=cw_lr,
            random_state=random_state,
        )),
    ])

    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        class_weight=cw_rf,
    )

    estimators: list[tuple[str, object]] = [
        ("logreg", logreg_pipeline),
        ("rf", rf),
    ]

    try:
        import xgboost as xgb  # noqa: PLC0415
        spw = 1.5 if enable_class_weights else 1.0
        xgb_clf = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=5,
            learning_rate=0.05,
            scale_pos_weight=spw,
            eval_metric="logloss",
            random_state=random_state,
            verbosity=0,
        )
        estimators.append(("xgb", xgb_clf))
    except ImportError:
        pass  # xgboost not installed; ensemble uses logreg + rf only

    return VotingClassifier(estimators=estimators, voting="soft")
