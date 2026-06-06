# Core configuration constants for AGRIVA EWS API

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/app/raw_data"
MODEL_DIR = "/app/models_output"

FEATURES_EWS = [
    'Rainfall', 'SPI - 3 months', 'Temperature',
    'Water Satisfaction Index (WSI)', 'Solar Radiation',
    'Soil Moisture (gapfilled historical time series)',
    'FPAR', 'FPAR - zscore', 'month_extracted'
]

TARGET_FORECAST_COLS = [
    'Rainfall', 'SPI - 3 months', 'Temperature',
    'Water Satisfaction Index (WSI)', 'Solar Radiation',
    'Soil Moisture (gapfilled historical time series)',
    'FPAR', 'FPAR - zscore'
]
