"""
ML module isolation.
Loads persisted pipelines/models and exposes them through a stable interface.
"""
from __future__ import annotations

import os
from typing import Any

import joblib

from shared import ews_pipeline, forecast_model


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
        path = os.path.join(get_model_dir(), "agriva_master_forecaster.pkl")
    if os.path.exists(path):
        return joblib.load(path)
    return None


def init_shared_state() -> None:
    global ews_pipeline, forecast_model
    ews_pipeline = load_ews_pipeline()
    forecast_model = load_forecast_model()
