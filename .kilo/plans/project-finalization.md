# Project Finalization Plan: AGRIVA EWS

## Phase 1: Repository Synchronization

### 1.1 Pre-Merge Audit
- Inspect the current branch (`feature/connect-backend-frontend`) for uncommitted/staged changes
- Review recent diverged commits between current branch and `remotes/origin/main`
- Identify merge conflict hotspots: `docker-compose.yml`, `docker-compose.frontend.yml`, `frontend/app.js`

### 1.2 Fetch and Rebase
- Run `git fetch origin` to update remote tracking refs
- Rebase current branch onto `origin/main` (preferred over merge to maintain linear history):
  ```bash
  git rebase origin/main
  ```
- **Conflict Resolution Strategy:**
  - `docker-compose.yml`: Keep the new `agriva_network` external network block from the feature branch; discard any stale service duplicates from main
  - `frontend/app.js`: Preserve relative `/api/` endpoint refactors from the feature branch; ensure no absolute URLs remain
  - `docker-compose.frontend.yml`: Keep Nginx proxy block and external network attachment from feature branch
  - Resolve conflicts iteratively with `git rebase --continue`; abort only if unresolvable

### 1.3 Post-Rebase Verification
- Run `git log --oneline` to confirm linear history
- Run `git status` to confirm clean working tree
- Push rebased branch: `git push --force-with-lease origin feature/connect-backend-frontend`

---

## Phase 2: Data and Model Integration

### 2.1 Database Schema — New 6-Month Forecast Table
Create a new SQLAlchemy model in `backend/models.py`:

```python
class Forecast6Month(Base):
    """
    Aggregated 6-month forecast data per province.
    Derived from forecast_feature and ews_forecast_result.
    Stores pre-computed dekad-level aggregates (monthly and semester)
    for fast frontend querying.
    """
    __tablename__ = "forecast_6month"

    id            = Column(Integer, primary_key=True, index=True)
    province_id   = Column(Integer, ForeignKey("province.id"), nullable=False, index=True)
    batch_id      = Column(Integer, ForeignKey("forecast_batch.id"), nullable=False, index=True)
    month         = Column(Integer, nullable=False)
    year          = Column(Integer, nullable=False)

    # Monthly aggregated features
    rainfall        = Column(Float, nullable=True)
    spi_3_months    = Column(Float, nullable=True)
    temperature     = Column(Float, nullable=True)
    wsi             = Column(Float, nullable=True)
    solar_radiation = Column(Float, nullable=True)
    soil_moisture   = Column(Float, nullable=True)
    fpar            = Column(Float, nullable=True)
    fpar_zscore     = Column(Float, nullable=True)

    # Aggregated EWS classification
    semester_extracted = Column(Integer, nullable=False)  # 1 = Jan-Jun, 2 = Jul-Dec
    ews_label          = Column(Integer, nullable=False)
    ews_probability    = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("province_id", "batch_id", "month", "year",
                         name="_f6m_province_batch_month_year_uc"),
    )
```

Add relationship in `Province`:
```python
forecast_6months = relationship("Forecast6Month", back_populates="province")
```

Add relationships in `ForecastBatch`:
```python
forecast_6months = relationship("Forecast6Month", back_populates="batch")
```

### 2.2 Repository Layer
Add `Forecast6MonthRepository` in `backend/repositories/forecast_repo.py`:

```python
class Forecast6MonthRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert(self, **kwargs) -> models.Forecast6Month:
        record = models.Forecast6Month(**kwargs)
        self.db.merge(record)
        self.db.flush()
        return record

    def get_by_batch(self, batch_id: int) -> list[models.Forecast6Month]:
        return (
            self.db.query(models.Forecast6Month)
            .filter(models.Forecast6Month.batch_id == batch_id)
            .all()
        )

    def get_latest_by_province(self, province_id: int, batch_id: int):
        return (
            self.db.query(models.Forecast6Month)
            .filter(
                models.Forecast6Month.province_id == province_id,
                models.Forecast6Month.batch_id == batch_id,
            )
            .order_by(models.Forecast6Month.year.asc(), models.Forecast6Month.month.asc())
            .all()
        )
```

### 2.3 Model Integration in Forecast Pipeline
Update `backend/services/forecast_service.py::execute_batch_forecast`:

1. After generating dekad-level `ForecastFeature` and `EWSForecastResult` records (existing loop), aggregate them into monthly buckets:
   - Group dekads by `(province_id, year, month)`
   - Compute mean features for `rainfall`, `spi_3_months`, `temperature`, `wsi`, `solar_radiation`, `soil_moisture`, `fpar`, `fpar_zscore`
   - Determine monthly EWS label: majority vote across dekads within the month; probability = mean probability

2. Also compute semester-level aggregation (months 1–6 → semester 1, months 7–12 → semester 2) for the 6-month window:
   - Group monthly rows by `(province_id, year, semester_extracted)`
   - Take mean features and majority-vote EWS label

3. Persist `Forecast6Month` records via `Forecast6MonthRepository` before setting `batch.status = "done"`.

---

## Phase 3: Validation and Testing

### 3.1 Database Integrity Validation
1. **Schema Verification**
   - Run `python -c "from backend.database import init_db; init_db(); from backend import models; models.Base.metadata.create_all(models.engine); print('OK')"` 
   - Confirm `forecast_6month` table exists with correct columns via psql or ORM inspection

2. **Schema Diff Check**
   - Compare ORM `Base.metadata.tables` keys against expected table list (including new `forecast_6month`)

3. **Referential Integrity**
   - Verify all `Forecast6Month.province_id` values exist in `province.id`
   - Verify all `Forecast6Month.batch_id` values exist in `forecast_batch.id`
   - Verify batch_id references point to `status="done"` batches

4. **Uniqueness Constraint Check**
   - Attempt duplicate insert for same `(province_id, batch_id, month, year)` and confirm `IntegrityError` is raised

### 3.2 Functional Testing Protocol
- **Employ pytest** (install if absent: `pip install pytest httpx`) to create `backend/tests/test_forecast_pipeline.py`:

```python
def test_forecast_batch_creates_features_and_results(db_session):
    """Execute a mini forecast batch and verify ForecastFeature and EWSForecastResult rows."""
    ...

def test_forecast_6month_populated_after_batch(db_session):
    """After batch completion, verify forecast_6month has exactly 6 rows per province."""

def test_forecast_6month_values_are_aggregates(db_session):
    """Compare forecast_6month.rainfall against corresponding forecast_feature mean."""

def test_province_based_cluster_integrity(db_session):
    """Ensure cluster_used in EWSForecastResult matches Province.cluster_wilayah."""

def test_api_forecast_predict_endpoint(client):
    """Call /api/forecast/predict and validate response shape."""

def test_api_ews_map_endpoint(client):
    """Call /api/ews-map after batch and validate province data presence."""
```

- Run full suite: `cd backend && python -m pytest tests/ -v`
- Also manually trigger forecast via API: `POST /api/forecast/predict` (or equivalent trigger) and inspect DB rows

### 3.3 Regression Checks
- Verify existing endpoints (`/api/health`, `/api/forecast/dashboard`, `/api/forecast/history`, `/api/predict/ews`) still return expected shapes
- Confirm frontend HTTP calls resolve against relative `/api/*` paths without CORS issues
- Verify Docker containers start correctly with shared network (`agriva_network`)

---

## Phase 4: Debugging and Quality Assurance

### 4.1 Mandatory Code Review Checklist
| Area | Check |
|------|-------|
| `models.py` | New table has correct FK targets, constraints, column types |
| `forecast_repo.py` | Repository methods use `merge`/`flush` correctly; no N+1 in new query methods |
| `forecast_service.py` | Monthly aggregation logic handles months with partial dekads; batch status transition is atomic |
| Import cycle | Verify no circular imports added by new model/repository in `forecast_service.py` |
| Type safety | SQLAlchemy 2.0 style consistency across new code |
| Error handling | New aggregation loop has try/except that rolls back properly on failure |

### 4.2 Common Issue Remediation
- **ImportError due to `models.py` circular imports**: Ensure `_forecast_6month` and relationship strings use lazy string references
- **Missing `semester_extracted` logic**: Confirm semester boundaries (Jan–Jun / Jul–Dec) match business rules
- **Float precision drift**: Use `round(..., 4)` when storing aggregated probabilities to avoid floating-point noise
- **Batch race condition**: Ensure only one forecast batch runs at a time (consider adding `batch.status` check at loop start with advisory lock or `FOR UPDATE SKIP LOCKED`)

### 4.3 Static Analysis
- Run `ruff check .` (or `flake8` if ruff unavailable) across `backend/`
- Run `mypy backend/` (if configured in project)

---

## Phase 5: Deployment and Version Control

### 5.1 Commit Sequence (All on `feature/connect-backend-frontend`)
1. `feat(db): add forecast_6month table and repository for 6-month aggregated forecast`
2. `feat(service): update forecast pipeline to populate forecast_6month table`
3. `test(forecast): add integration tests for 6-month table population and integrity`
4. `chore: final verification and cleanup pre-merge`

Each commit should be signed with `--no-verify` skipped (use standard hooks) and message format: `type(scope): description`.

### 5.2 Merge to Main
1. Push all commits: `git push origin feature/connect-backend-frontend`
2. Via GitHub CLI (or web UI) open a PR: `gh pr create --base main --head feature/connect-backend-frontend --title "feat: finalize AGRIVA EWS with 6-month forecast table and frontend integration"`
3. After CI passes and manual review confirms:
   ```bash
   git checkout main
   git pull origin main
   git merge feature/connect-backend-frontend --no-ff
   git push origin main
   ```
4. Tag the release: `git tag -a v2.5.0-forecast-final -m "final: 6-month forecast table, docker network sync, EWS pipeline complete"` && `git push origin v2.5.0-forecast-final`
5. Delete feature branch: `git branch -d feature/connect-backend-frontend` and `git push origin --delete feature/connect-backend-frontend`

### 5.3 Post-Merge Deployment
- Rebuild Docker images: `docker compose build --no-cache` (both compose files if network is externalized)
- Migrate database schema: `docker compose exec backend python -c "from database import init_db; init_db()"` or run Alembic migration if available
- Restart services: `docker compose down && docker compose up -d`
- Verify: `curl http://localhost:8001/api/health` and `curl http://localhost:5174`

---

## Summary of New Files/Changes
| Path | Action |
|------|--------|
| `backend/models.py` | Add `Forecast6Month` class + relationships |
| `backend/repositories/forecast_repo.py` | Add `Forecast6MonthRepository` |
| `backend/services/forecast_service.py` | Add 6-month aggregation + persistence logic |
| `backend/tests/test_forecast_pipeline.py` | New test suite |
| `.kilo/plans/project-finalization.md` | This plan |
