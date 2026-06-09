# Revised Database & Integration Plan: Map-Optimized 6-Month Forecast

## Revision Context

The previous plan included a `semester_extracted` column and semester-level aggregation. That structure is **removed**. The new design prioritizes the database's primary consumer: the frontend map interface, which filters by `month` and `year` and displays province-level risk projections 6 months into the future.

---

## 1. Revised Data Model: `forecast_monthly`

**Table purpose:** Store monthly-aggregated 6-month forecast data for the map interface. One row per province per month per forecast batch.

```python
class ForecastMonthly(Base):
    """
    Monthly-aggregated 6-month forecast for map interface.
    Primary consumer: /api/ews-map and future forecast-map endpoints.
    Replaces the dekad-level join pattern with a single optimized table.
    """
    __tablename__ = "forecast_monthly"

    id              = Column(Integer, primary_key=True, index=True)
    province_id     = Column(Integer, ForeignKey("province.id"), nullable=False, index=True)
    batch_id        = Column(Integer, ForeignKey("forecast_batch.id"), nullable=False, index=True)

    month           = Column(Integer, nullable=False)   # 1-12
    year            = Column(Integer, nullable=False)
    forecast_date   = Column(Date, nullable=False)      # dekad date used for this month's aggregate

    # Monthly-mean forecasted features (from model_forecast_global.pkl)
    rainfall        = Column(Float, nullable=True)
    spi_3_months    = Column(Float, nullable=True)
    temperature     = Column(Float, nullable=True)
    wsi             = Column(Float, nullable=True)
    solar_radiation = Column(Float, nullable=True)
    soil_moisture   = Column(Float, nullable=True)
    fpar            = Column(Float, nullable=True)
    fpar_zscore     = Column(Float, nullable=True)

    # EWS classification (majority vote + mean probability across dekads in month)
    ews_label       = Column(Integer, nullable=False)   # 0 or 1
    ews_probability = Column(Float, nullable=False)
    dekad_count     = Column(Integer, nullable=False, default=0)  # how many dekads rolled up

    __table_args__ = (
        UniqueConstraint("province_id", "batch_id", "month", "year",
                         name="_fm_province_batch_month_year_uc"),
    )

    province = relationship("Province", back_populates="forecast_monthlies")
    batch    = relationship("ForecastBatch", back_populates="forecast_monthlies")
```

**Add relationships:**
- `Province.forecast_monthlies = relationship("ForecastMonthly", back_populates="province")`
- `ForecastBatch.forecast_monthlies = relationship("ForecastMonthly", back_populates="batch")`

**Why this design:**
- Matches frontend filter params exactly: `month` + `year` → direct WHERE clause, no date range math
- Eliminates the 3-table JOIN pattern (`Province` + `ForecastFeature` + `EWSForecastResult`) that `/api/ews-map` currently uses
- Stores the dekad-level data's aggregation in a single read-optimized row
- `forecast_date` preserves the temporal anchor (last dekad of the month) for ordering
- `dekad_count` handles edge cases where a month at the forecast boundary has fewer than 3 dekads

---

## 2. Repository Layer: `ForecastMonthlyRepository`

**File:** `backend/repositories/forecast_repo.py`

```python
class ForecastMonthlyRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert(self, **kwargs) -> models.ForecastMonthly:
        """Merge to avoid duplicate key errors on re-runs."""
        record = models.ForecastMonthly(**kwargs)
        self.db.merge(record)
        self.db.flush()
        return record

    def get_by_batch_and_period(self, batch_id: int, month: int = None, year: int = None) -> list[models.ForecastMonthly]:
        query = self.db.query(models.ForecastMonthly).filter(
            models.ForecastMonthly.batch_id == batch_id
        )
        if month is not None:
            query = query.filter(models.ForecastMonthly.month == month)
        if year is not None:
            query = query.filter(models.ForecastMonthly.year == year)
        return query.all()

    def get_latest_by_province(self, province_id: int, batch_id: int):
        return (
            self.db.query(models.ForecastMonthly)
            .filter(
                models.ForecastMonthly.province_id == province_id,
                models.ForecastMonthly.batch_id == batch_id,
            )
            .order_by(models.ForecastMonthly.year.asc(), models.ForecastMonthly.month.asc())
            .all()
        )
```

---

## 3. Service Layer Update: `forecast_service.py`

**File:** `backend/services/forecast_service.py`

**Change in `execute_batch_forecast()`:**

Replace the existing dekad-level loop's final step. After all dekads are generated for a province (the inner `for step in range(steps)` loop), add a monthly aggregation phase:

1. **Query back the dekad-level records** just inserted for this `(province_id, batch_id)`:
   ```python
   dekads = (
       db.query(models.ForecastFeature, models.EWSForecastResult)
       .join(models.EWSForecastResult,
             models.ForecastFeature.province_id == models.EWSForecastResult.province_id)
       .filter(models.ForecastFeature.province_id == prov.id)
       .filter(models.ForecastFeature.batch_id == batch_id)
       .filter(models.EWSForecastResult.batch_id == batch_id)
       .filter(models.ForecastFeature.forecast_date == models.EWSForecastResult.forecast_date)
       .order_by(models.ForecastFeature.forecast_date.asc())
       .all()
   )
   ```

2. **Group by (year, month)** and compute:
   - `rainfall`, `spi_3_months`, `temperature`, `wsi`, `solar_radiation`, `soil_moisture`, `fpar`, `fpar_zscore` → **mean** of dekad values
   - `ews_label` → **majority vote** (if tie, `ews_probability` mean breaks it → round to 1 if mean ≥ 0.5)
   - `ews_probability` → **mean** of dekad probabilities
   - `forecast_date` → **max** forecast_date within the month (the last dekad's date)
   - `dekad_count` → count of dekads in the group

3. **Persist via `ForecastMonthlyRepository.upsert()`**

4. **Only after all monthly records are persisted**, set `batch.status = "done"`

**No semester-level logic.** The pipeline produces exactly `months_ahead` monthly rows per province (e.g., 6 months = 6 rows).

---

## 4. Router Updates for Map Interface

**File:** `backend/routers/forecast.py` (for `/api/ews-map`) and `backend/routers/map.py` (for `/api/map/data`)

### 4.1 Rewrite `/api/ews-map` to use `forecast_monthly`

Current implementation joins 3 tables on `forecast_date`. Replace with a single query on `ForecastMonthly`:

```python
@router.get("/api/ews-map")
def get_ews_map(
    month: int = None,
    year: int = None,
    cluster: str = None,
    ews_label: int = None,
    db: Session = Depends(get_db)
):
    latest_batch = db.query(models.ForecastBatch).filter(
        models.ForecastBatch.status == "done"
    ).order_by(models.ForecastBatch.created_at.desc()).first()

    if not latest_batch:
        return {"provinces": [], "message": "No forecast batch has completed successfully yet."}

    query = (
        db.query(models.Province, models.ForecastMonthly)
        .join(models.ForecastMonthly, models.ForecastMonthly.province_id == models.Province.id)
        .filter(models.ForecastMonthly.batch_id == latest_batch.id)
    )

    if month is not None:
        query = query.filter(models.ForecastMonthly.month == month)
    if year is not None:
        query = query.filter(models.ForecastMonthly.year == year)
    if cluster is not None and cluster != "all":
        query = query.filter(models.Province.cluster_wilayah == int(cluster))
    if ews_label is not None:
        query = query.filter(models.ForecastMonthly.ews_label == ews_label)

    results = query.all()

    provinces_data = []
    for prov, fm in results:
        provinces_data.append({
            "province_id": prov.id,
            "province_name": prov.name,
            "latitude": prov.latitude,
            "longitude": prov.longitude,
            "cluster_wilayah": prov.cluster_wilayah,
            "forecast_date": fm.forecast_date.strftime('%Y-%m-%d'),
            "month": fm.month,
            "year": fm.year,
            "rainfall": fm.rainfall,
            "spi_3_months": fm.spi_3_months,
            "temperature": fm.temperature,
            "wsi": fm.wsi,
            "solar_radiation": fm.solar_radiation,
            "soil_moisture": fm.soil_moisture,
            "fpar": fm.fpar,
            "fpar_zscore": fm.fpar_zscore,
            "ews_label": fm.ews_label,
            "ews_probability": fm.ews_probability,
            "cluster_used": prov.cluster_wilayah,
            "dekad_count": fm.dekad_count,
        })

    return {"batch_id": latest_batch.id, "created_at": latest_batch.created_at, "provinces": provinces_data}
```

### 4.2 Rewrite `/api/ews-map/provinces/{province_id}` similarly

```python
@router.get("/api/ews-map/provinces/{province_id}")
def get_ews_map_province(province_id: int, db: Session = Depends(get_db)):
    latest_batch = db.query(models.ForecastBatch).filter(
        models.ForecastBatch.status == "done"
    ).order_by(models.ForecastBatch.created_at.desc()).first()

    if not latest_batch:
        raise HTTPException(status_code=404, detail="No forecast batch completed yet.")

    results = (
        db.query(models.ForecastMonthly)
        .filter(models.ForecastMonthly.province_id == province_id)
        .filter(models.ForecastMonthly.batch_id == latest_batch.id)
        .order_by(models.ForecastMonthly.year.asc(), models.ForecastMonthly.month.asc())
        .all()
    )

    data = []
    for fm in results:
        data.append({
            "forecast_date": fm.forecast_date.strftime('%Y-%m-%d'),
            "month": fm.month,
            "year": fm.year,
            "rainfall": fm.rainfall,
            "temperature": fm.temperature,
            "wsi": fm.wsi,
            "spi_3_months": fm.spi_3_months,
            "soil_moisture": fm.soil_moisture,
            "fpar": fm.fpar,
            "ews_label": fm.ews_label,
            "ews_probability": fm.ews_probability,
            "dekad_count": fm.dekad_count,
        })

    return {"province_id": province_id, "latest_batch_id": latest_batch.id, "data": data}
```

---

## 5. Frontend Compatibility Verification

**File to inspect:** `frontend/app.js`

### 5.1 API constant alignment
- Current: `const API = "http://localhost:8001";`
- Milestone 1 (already on this branch) converts frontend to relative `/api/` paths via Nginx proxy
- Verify: `app.js` currently mixes absolute `API + "/api/..."` calls and one relative call (`fetch('https://raw.githubusercontent.com/...')` for GeoJSON which is external CDN, unaffected)
- **Action:** No change needed to `app.js` for this iteration — the `API` constant already points to the backend. After Docker network setup, Nginx proxies `/api/` to backend.

### 5.2 Map data flow check
- `loadMapData()` (app.js:117) calls `fetch(`${API}/api/map/data?year=${year}&month=${month}`)`
- `/api/ews-map` is currently called elsewhere? Need to verify if the map page actually uses `/api/ews-map` or `/api/map/data`
- **Finding from code review:** The map page uses `/api/map/data` (historical data). The `/api/ews-map` endpoint exists but may not be called from the current frontend map code.
- **Gap:** The map currently shows `HistoricalMetric` data. To show forecast data on the map, we need either:
  - **Option A:** Add forecast data to `/api/map/data` response (add a `forecast` flag parameter)
  - **Option B:** Ensure the frontend also calls `/api/ews-map` for forecast projection display (e.g., a "Proyeksi 6 Bulan" toggle button)
- **Recommendation:** Add a `mode=forecast` query param to `/api/map/data` that switches to querying `ForecastMonthly` + `EWSForecastResult` (or just `ForecastMonthly` which now contains both). This keeps the frontend call pattern unchanged.

### 5.3 Response shape compatibility

Current `/api/ews-map` response fields used by `app.js`:
- `province_id` → used? Not directly in map code (map uses province name from GeoJSON)
- `province_name` → used in popup
- `latitude`, `longitude` → used for positioning
- `cluster_wilayah` → used for cluster filtering
- `forecast_date` → used in popup
- `rainfall` → mapped to `avg_rainfall` in popup
- `temperature` → mapped to `avg_temperature`
- `wsi` → not directly displayed in popup, but in chart
- `spi_3_months` → mapped to `avg_spi`
- `ews_label` → mapped to `warning_code` (1 = risk, 0 = safe)
- `ews_probability` → displayed as confidence
- `cluster_used` → matches `cluster_wilayah`

**The new `forecast_monthly` table returns all these fields.** The frontend popup template in `app.js:175` references `info.avg_rainfall`, `info.avg_temperature`, `info.avg_spi`, `info.cluster`, `info.warning_code`, `info.warning`. These field names come from `/api/map/data` (current) which uses different key names than `/api/ews-map`.

**Key gap to resolve:** The frontend map data consumption expects keys like `avg_rainfall`, `avg_temperature`, `avg_spi`, `warning`, `warning_code` from `/api/map/data`. The `/api/ews-map` endpoint returns `rainfall`, `temperature`, `spi_3_months`, `ews_label` (no `warning` string).

**Fix needed in backend: `/api/map/data` must return keys matching what `app.js` expects, OR `app.js` must be updated to consume the `/api/ews-map` key names.**

**Proposed approach:** Update `/api/map/data` to support forecast mode. Keep backward compatibility for historical mode. The response keys should remain `avg_rainfall`, `avg_temperature`, `avg_spi`, `warning`, `warning_code` to avoid frontend changes.

```python
@router.get("/api/map/data")
def map_data(year: Optional[str] = None, month: Optional[str] = None,
             mode: str = "historical",  # NEW: "historical" or "forecast"
             db: Session = Depends(get_db)):
    ...
    if mode == "forecast":
        latest_batch = db.query(models.ForecastBatch).filter(
            models.ForecastBatch.status == "done"
        ).order_by(models.ForecastBatch.created_at.desc()).first()
        if not latest_batch:
            return {"provinces": [], "message": "No forecast data available."}

        metrics = (
            db.query(models.Province, models.ForecastMonthly)
            .join(models.ForecastMonthly, models.ForecastMonthly.province_id == models.Province.id)
            .filter(models.ForecastMonthly.batch_id == latest_batch.id)
            ...
        )
        # Build result with same key names: avg_rainfall, avg_temperature, avg_spi, warning, warning_code
    else:
        # existing HistoricalMetric logic
```

---

## 6. Docker Deployment Verification

### 6.1 Compose file sanity
**File:** `docker-compose.yml`
- Verify `agriva_network` is defined and all 3 services (db, backend, frontend) attach to it
- Verify backend volume mounts don't reference deleted paths (from the backend tidying plan)
- Verify no stale dependencies

### 6.2 Build and test sequence
```bash
# Validate compose config
docker compose config

# Rebuild backend (new model + code)
docker compose build backend

# Start or restart stack
docker compose down
docker compose up -d

# Wait for readiness, then verify
curl http://localhost:8001/api/health
curl http://localhost:5174
```

### 6.3 Database migration
- Since this project doesn't use Alembic, rely on `init_db()` in `main.py` which calls `Base.metadata.create_all()`
- On container restart, `init_db()` will create the new `forecast_monthly` table automatically
- **Risk:** `create_all` won't alter existing tables (safe for new table addition), but won't backfill data. A new forecast batch run will populate it.

---

## 7. Full Integration Test Protocol

### 7.1 Backend tests

**New test file:** `backend/tests/test_forecast_monthly.py`

```python
def test_forecast_monthly_schema_created(db_session):
    """Verify forecast_monthly table exists with all columns."""
    from sqlalchemy import inspect
    insp = inspect(db_session.bind)
    assert "forecast_monthly" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("forecast_monthly")}
    assert cols == {"id", "province_id", "batch_id", "month", "year", "forecast_date",
                    "rainfall", "spi_3_months", "temperature", "wsi",
                    "solar_radiation", "soil_moisture", "fpar", "fpar_zscore",
                    "ews_label", "ews_probability", "dekad_count"}

def test_forecast_monthly_populated_after_batch(db_session):
    """After batch completes, expect months_ahead rows per province in forecast_monthly."""
    # Trigger a batch with months_ahead=6, then verify 6 rows per province

def test_forecast_monthly_values_are_monthly_means(db_session):
    """Compare forecast_monthly.rainfall against mean of ForecastFeature.rainfall for same month."""

def test_ews_label_is_majority_vote(db_session):
    """Verify ews_label matches majority of dekad-level ews_label values for that month."""

def test_api_ews_map_uses_forecast_monthly(client, db_session):
    """Call /api/ews-map and verify response includes forecast_monthly fields."""

def test_api_map_data_forecast_mode(client, db_session):
    """Call /api/map/data?mode=forecast and verify response shape matches historical mode keys."""
```

Run: `cd backend && python -m pytest tests/ -v`

### 7.2 Frontend compatibility tests

**Manual browser test:**
1. Load `http://localhost:5174`
2. Navigate to Peta Risiko (map page)
3. Verify map renders with province polygons
4. Click "Terapkan Filter" — verify data loads (stats update, provinces colored)
5. Switch to forecast mode (if implemented as toggle) — verify map shows forecasted risk for next 6 months
6. Click a province — verify popup shows correct data (rainfall, temperature, SPI, risk status)

**API contract test (scripted):**
```python
def test_frontend_api_contract():
    """Verify all frontend API calls have matching backend endpoints with correct response shapes."""
    # GET /api/map/filters → {years, months}
    # GET /api/map/data?year=&month=&mode=historical → {provinces: [{province, warning, warning_code, cluster, avg_rainfall, avg_temperature, avg_spi}]}
    # GET /api/map/data?year=&month=&mode=forecast → same shape (from forecast_monthly)
    # GET /api/ews-map → {batch_id, created_at, provinces: [{...same keys...}]}
    # GET /api/ews-map/provinces/{id} → {province_id, latest_batch_id, data: [{forecast_date, ...}]}
```

### 7.3 Docker deployment smoke test

```bash
# Container health
docker compose ps
# Both backend and frontend should be "Up"

# Backend API
curl -s http://localhost:8001/api/health | jq .
# → {"status":"ok"}

# Frontend accessibility
curl -s http://localhost:5174 | head -20
# → HTML content with AGRIVA title

# Map data endpoint
curl -s "http://localhost:8001/api/map/data?year=2026&month=4&mode=forecast" | jq '.provinces[0]'
# → Should return province with forecast_monthly fields

# EWS map endpoint
curl -s "http://localhost:8001/api/ews-map?month=4&year=2026" | jq '.provinces[0]'
# → Should return province with forecast data

# CORS check
curl -s -H "Origin: http://localhost:5174" -I http://localhost:8001/api/health
# → Access-Control-Allow-Origin: *
```

---

## 8. Backend Tidying (from previous plan, unchanged)

- Delete `backend/routers/__init__.py` (empty, namespace packages implicit)
- Delete 8 `__pycache__/` directories
- Do NOT touch `backend/models_output/`, `backend/raw_data/`, or anything outside `backend/`

---

## 9. Commit and Merge Sequence

1. `refactor: tidy backend — remove empty __init__.py and __pycache__`
2. `feat(db): add forecast_monthly table for map-optimized 6-month forecast`
3. `feat(repo): add ForecastMonthlyRepository`
4. `feat(service): aggregate dekad forecasts into monthly rows in execute_batch_forecast`
5. `feat(router): rewrite /api/ews-map and /api/map/data to use forecast_monthly`
6. `test: add integration tests for forecast_monthly pipeline and API contract`
7. `chore: final verification and pre-merge cleanup`

Push → PR → CI → Merge to `main` → Tag `v2.6.0-forecast-monthly` → Deploy
