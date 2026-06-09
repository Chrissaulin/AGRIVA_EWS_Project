import pytest
from sqlalchemy import inspect

from database import SessionLocal
from models import ForecastMonthly, ForecastFeature, Province, ForecastBatch


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_forecast_monthly_schema_created(db_session):
    insp = inspect(db_session.bind)
    assert "forecast_monthly" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("forecast_monthly")}
    assert cols == {
        "id", "province_id", "batch_id", "month", "year", "forecast_date",
        "rainfall", "spi_3_months", "temperature", "wsi",
        "solar_radiation", "soil_moisture", "fpar", "fpar_zscore",
        "ews_label", "ews_probability", "dekad_count",
    }


def test_forecast_monthly_values_are_monthly_means(db_session):
    db_session.query(ForecastMonthly).delete()
    db_session.commit()

    prov = db_session.query(Province).first()
    if prov is None:
        pytest.skip("No province data")

    batch = ForecastBatch(months_ahead=1, status="done", total_provinces=1)
    db_session.add(batch)
    db_session.flush()

    rows = [
        ForecastFeature(
            province_id=prov.id, batch_id=batch.id, forecast_date="2026-04-10",
            month=4, year=2026, dekad_id=1,
            rainfall=10.0, spi_3_months=0.5, temperature=27.0, wsi=0.6,
            solar_radiation=100.0, soil_moisture=0.4, fpar=0.3, fpar_zscore=-0.1,
        ),
        ForecastFeature(
            province_id=prov.id, batch_id=batch.id, forecast_date="2026-04-20",
            month=4, year=2026, dekad_id=2,
            rainfall=20.0, spi_3_months=0.6, temperature=28.0, wsi=0.7,
            solar_radiation=110.0, soil_moisture=0.5, fpar=0.4, fpar_zscore=0.0,
        ),
        ForecastFeature(
            province_id=prov.id, batch_id=batch.id, forecast_date="2026-04-30",
            month=4, year=2026, dekad_id=3,
            rainfall=30.0, spi_3_months=0.7, temperature=29.0, wsi=0.8,
            solar_radiation=120.0, soil_moisture=0.6, fpar=0.5, fpar_zscore=0.1,
        ),
    ]
    db_session.add_all(rows)
    db_session.flush()

    from services.forecast_service import _to_monthly_records
    monthly = _to_monthly_records([
        {
            "province_id": prov.id, "batch_id": batch.id,
            "forecast_date": r.forecast_date, "month": r.month, "year": r.year,
            "rainfall": r.rainfall, "spi_3_months": r.spi_3_months,
            "temperature": r.temperature, "wsi": r.wsi,
            "solar_radiation": r.solar_radiation, "soil_moisture": r.soil_moisture,
            "fpar": r.fpar, "fpar_zscore": r.fpar_zscore,
            "ews_label": 1, "ews_probability": 0.7,
        }
        for r in rows
    ])

    assert len(monthly) == 1
    m = monthly[0]
    assert m["month"] == 4
    assert m["year"] == 2026
    assert abs(m["rainfall"] - 20.0) < 1e-9
    assert abs(m["temperature"] - 28.0) < 1e-9
    assert m["ews_label"] == 1
    assert m["dekad_count"] == 3


def test_ews_label_is_majority_vote(db_session):
    db_session.query(ForecastMonthly).delete()
    db_session.commit()

    prov = db_session.query(Province).first()
    if prov is None:
        pytest.skip("No province data")

    batch = ForecastBatch(months_ahead=1, status="done", total_provinces=1)
    db_session.add(batch)
    db_session.flush()

    from services.forecast_service import _to_monthly_records
    rows = [
        {"ews_label": 0, "ews_probability": 0.4, "month": 5, "year": 2026,
         "forecast_date": "2026-05-10", "rainfall": 10, "spi_3_months": 0.1,
         "temperature": 27, "wsi": 0.5, "solar_radiation": 100, "soil_moisture": 0.3,
         "fpar": 0.2, "fpar_zscore": -0.2},
        {"ews_label": 0, "ews_probability": 0.4, "month": 5, "year": 2026,
         "forecast_date": "2026-05-20", "rainfall": 11, "spi_3_months": 0.2,
         "temperature": 27.5, "wsi": 0.55, "solar_radiation": 105, "soil_moisture": 0.35,
         "fpar": 0.25, "fpar_zscore": -0.15},
        {"ews_label": 1, "ews_probability": 0.8, "month": 5, "year": 2026,
         "forecast_date": "2026-05-30", "rainfall": 12, "spi_3_months": 0.3,
         "temperature": 28, "wsi": 0.6, "solar_radiation": 110, "soil_moisture": 0.4,
         "fpar": 0.3, "fpar_zscore": -0.1},
    ]
    monthly = _to_monthly_records(rows)
    assert monthly[0]["ews_label"] == 0
    assert abs(monthly[0]["ews_probability"] - (0.4 + 0.4 + 0.8) / 3) < 1e-9
