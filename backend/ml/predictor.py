"""
Predictor module.
Wraps XGBoost inference so services do not touch joblib/pipeline internals.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


class EWSPredictor:
    @staticmethod
    def predict(pipeline: Any, features: pd.DataFrame, threshold: float = 0.5) -> dict:
        cols = list(pipeline.feature_names_in_)
        prepared = features.reindex(columns=cols, fill_value=0)
        proba = pipeline.predict_proba(prepared)[0]
        prob_risk = float(proba[1])
        return {
            "Probability(risk)": prob_risk,
            "label": 1 if prob_risk >= threshold else 0,
            "threshold": threshold,
        }
