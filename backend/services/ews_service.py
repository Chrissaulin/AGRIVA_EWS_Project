"""
EWS prediction service.
Encapsulates the XGBoost classifier inference so routers and forecast
service can reuse identical logic.
"""
from __future__ import annotations

import pandas as pd

import ml.loader as ml_loader


def resolve_pipeline(cluster_id: int):
    """Return (pipeline, threshold) for the given cluster."""
    ews_pipeline = ml_loader.ews_pipeline
    if not isinstance(ews_pipeline, dict):
        return ews_pipeline, 0.5

    cluster_dict = ews_pipeline.get(cluster_id, {})
    if isinstance(cluster_dict, dict) and "model_xgboost" in cluster_dict:
        return cluster_dict["model_xgboost"], cluster_dict.get("threshold_siaga", 0.5)
    return cluster_dict, 0.5


def predict_ews(
    cluster_id: int,
    features_df: pd.DataFrame,
    threshold: float | None = None,
    pipeline_override=None,
):
    """
    Run EWS binary classification.

    - If pipeline_override is provided, use it directly (caller already resolved it).
    - Otherwise resolve from shared.ews_pipeline by cluster_id.
    - features_df must already contain the columns the model expects.

    Returns dict: ews_label, ews_probability, threshold
    """
    if pipeline_override is not None:
        pipeline = pipeline_override
        threshold = threshold if threshold is not None else 0.5
    else:
        pipeline, threshold = resolve_pipeline(cluster_id)

    f_cols = list(pipeline.feature_names_in_)
    prepared = features_df.reindex(columns=f_cols, fill_value=0)
    proba = pipeline.predict_proba(prepared)[0]
    prob_berisiko = float(proba[1])
    label = 1 if prob_berisiko >= threshold else 0

    return {
        "ews_label": label,
        "ews_probability": prob_berisiko,
        "threshold": threshold,
    }
