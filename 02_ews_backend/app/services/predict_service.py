import pandas as pd
from app.schemas import SimulationInput, SimulationResponse

# Gold thresholds from 02_Modeling_AGRIVA.ipynb to achieve Sensitivity (Recall) >= 0.85
CLUSTER_THRESHOLDS = {
    0: 0.209,
    1: 0.276,
    2: 0.244
}

def predict_ews_risk(
    input_data: SimulationInput, 
    region_to_cluster: dict, 
    models: dict
) -> SimulationResponse:
    """
    Resolve the territory cluster of the target province, format inputs to match 
    Scikit-learn expected features, execute prediction pipeline, and evaluate against 
    custom recall-optimized thresholds.
    """
    region = input_data.region_name
    
    # 1. Resolve dynamic province-to-cluster assignment
    cluster_id = region_to_cluster.get(region)
    if cluster_id is None:
        # Dynamic fallback if province is not matched (defaulting to cluster 0)
        cluster_id = 0
        
    # 2. Retrieve corresponding model pipeline
    pipeline = models.get(f"pipeline_cluster_{cluster_id}")
    if not pipeline:
        raise ValueError(f"Classifier pipeline for Cluster {cluster_id} is not loaded.")
        
    # 3. Format input to match the training feature column names
    # Column order and names must exactly match:
    # ['Rainfall', 'SPI - 3 months', 'Temperature', 'Water Satisfaction Index (WSI)', 
    #  'Solar Radiation', 'Soil Moisture (gapfilled historical time series)', 
    #  'FPAR', 'FPAR - zscore', 'month_extracted']
    X = pd.DataFrame([{
        'Rainfall': input_data.rainfall,
        'SPI - 3 months': input_data.spi_3m,
        'Temperature': input_data.temperature,
        'Water Satisfaction Index (WSI)': input_data.wsi,
        'Solar Radiation': input_data.solar_radiation,
        'Soil Moisture (gapfilled historical time series)': input_data.soil_moisture,
        'FPAR': input_data.fpar,
        'FPAR - zscore': input_data.fpar_zscore,
        'month_extracted': input_data.month
    }])
    
    # 4. Extract probability of the warning class (class 1: Bahaya)
    # The pipeline automatically applies the StandardScaler fitting
    probabilities = pipeline.predict_proba(X)
    proba = float(probabilities[0, 1])
    
    # 5. Apply golden recall threshold
    threshold = CLUSTER_THRESHOLDS.get(cluster_id, 0.5)
    is_warning = proba >= threshold
    status_label = "Bahaya" if is_warning else "Aman"
    
    return SimulationResponse(
        region_name=region,
        cluster_wilayah=cluster_id,
        probability=round(proba, 4),
        threshold_used=threshold,
        is_warning=is_warning,
        status_label=status_label
    )
