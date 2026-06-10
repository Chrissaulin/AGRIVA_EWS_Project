"""
ML module isolation.
Loads persisted pipelines/models and exposes them through a stable interface.
"""
from __future__ import annotations

import os
from typing import Any

import joblib

# Module-level cache for models (set at app startup)
ews_pipeline: Any = None
forecast_model: Any = None


def get_model_dir() -> str:
    return "/app/models_output"


def load_ews_pipeline(path: str | None = None) -> Any:
    if path is None:
        path = os.path.join(get_model_dir(), "agriva_master_classifier.pkl")
    if os.path.exists(path):
        return joblib.load(path)
    return None


def load_forecast_model(path: str | None = None) -> Any:
    if path is None:
        # Try both filename variants (notebook uses 'forecasting', code expects 'forecaster')
        for name in ["agriva_master_forecasting.pkl", "agriva_master_forecaster.pkl"]:
            p = os.path.join(get_model_dir(), name)
            if os.path.exists(p):
                path = p
                break
    if path and os.path.exists(path):
        return joblib.load(path)
    return None


def set_models(ews_pipeline_obj: Any, forecast_model_obj: Any) -> None:
    """Update module-level cache (called at app startup)."""
    global ews_pipeline, forecast_model
    ews_pipeline = ews_pipeline_obj
    forecast_model = forecast_model_obj