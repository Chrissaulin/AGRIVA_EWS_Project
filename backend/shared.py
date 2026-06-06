"""
Shared global state for the AGRIVA EWS API.

Routers and services import state from here to avoid circular dependencies
with main.py. Functions are lazily imported from services to prevent
import-time cycles.
"""
from __future__ import annotations

# Global mutable state (populated at startup by main.load_resources)
ews_pipeline = None
forecast_model = None
PROVINCES_LIST: list[str] = []
CLUSTER_MAP: dict[str, int] = {}


def get_province_dataframe_with_features(*args, **kwargs):
    from services.feature_engineering import get_province_dataframe_with_features as _fn
    return _fn(*args, **kwargs)


def execute_batch_forecast(*args, **kwargs):
    from services.forecast_service import execute_batch_forecast as _fn
    return _fn(*args, **kwargs)
