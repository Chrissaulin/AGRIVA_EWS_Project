# Backend Folder Tidying Plan

**Scope:** Only `backend/` directory. Do NOT delete, gitignore, or modify any other folders (`01_dapur_jupyter/`, `03_ews_frontend/`, `frontend/`, `.kilo/`, etc.). Those are handled by other people.

**Constraint:** Be extremely careful with deletions. Verify each item's purpose before removing anything.

---

## Step 1: Audit Backend Folder Contents

### Current state of `backend/`:
```
backend/
├── core/                    ✅ Keep — contains config.py
│   ├── __pycache__/         🗑️ Cache — already gitignored in root .gitignore
│   └── config.py
├── ml/                      ✅ Keep — ML loader and predictor modules
│   ├── __pycache__/         🗑️ Cache
│   ├── __init__.py
│   ├── feature_builder.py
│   ├── loader.py
│   └── predictor.py
├── models_output/           ✅ KEEP — Docker volume mount point (empty but required)
├── raw_data/                ✅ KEEP — Docker volume mount point (empty but required)
├── repositories/            ✅ Keep — data access layer
│   ├── __pycache__/         🗑️ Cache
│   ├── forecast_repo.py
│   ├── metrics_repo.py
│   ├── province_repo.py
│   └── simulation_repo.py
├── routers/                 ✅ Keep — API route definitions
│   ├── __pycache__/         🗑️ Cache
│   ├── __init__.py          🗑️ EMPTY FILE — safe to remove (Python 3.3+ namespace packages, no imports depend on it)
│   ├── admin.py
│   ├── eda.py
│   ├── forecast.py
│   ├── map.py
│   ├── predict.py
│   └── simulate.py
├── schemas/                 ✅ Keep — Pydantic models
│   ├── __pycache__/         🗑️ Cache
│   ├── forecast.py
│   ├── predict.py
│   └── response_models.py
├── scripts/                 ✅ Keep — ETL seeder
│   ├── __pycache__/         🗑️ Cache
│   └── etl_seeder.py
├── services/                ✅ Keep — business logic
│   ├── __pycache__/         🗑️ Cache
│   ├── etl_service.py
│   ├── ews_service.py
│   ├── feature_engineering.py
│   ├── forecast_service.py
│   └── predict_service.py
├── __pycache__/             🗑️ Cache
├── .dockerignore            ✅ Keep — useful for Docker image builds
├── database.py              ✅ Keep
├── Dockerfile               ✅ Keep
├── main.py                  ✅ Keep
├── models.py                ✅ Keep
├── requirements.txt         ✅ Keep
└── shared.py                ✅ Keep
```

---

## Step 2: Safe Deletions

### 2.1 Remove empty `routers/__init__.py`
**Why safe:** 
- Python 3.3+ supports implicit namespace packages — `__init__.py` is not required
- All imports in `main.py` use explicit submodule paths: `from routers.eda import router`, `from routers.forecast import router`, etc.
- No code references `routers.__init__` or expects a package-level `__all__`
- File is completely empty (0 bytes)

**Action:** Delete `backend/routers/__init__.py`

### 2.2 Clean `__pycache__` directories
**Why safe:**
- Root `.gitignore` already contains `__pycache__/` and `*.pyc` — these are never committed
- Python auto-generates these on import; they're transient build artifacts
- 8 `__pycache__/` directories found across backend subdirectories

**Action:** Remove all `__pycache__/` directories from working tree:
- `backend/__pycache__/`
- `backend/core/__pycache__/`
- `backend/ml/__pycache__/`
- `backend/repositories/__pycache__/`
- `backend/routers/__pycache__/`
- `backend/schemas/__pycache__/`
- `backend/scripts/__pycache__/`
- `backend/services/__pycache__/`

### 2.3 DO NOT touch these
- `backend/models_output/` — Docker compose mounts `./01_dapur_jupyter/models` here as read-only volume. Directory must exist as a mount point even if empty in git.
- `backend/raw_data/` — Same reason, mounts `./01_dapur_jupyter/data` here.
- `backend/.dockerignore` — Properly configured, keeps images lean.
- Any `.pkl` files — per project rules, these are heavy ML models and should not be modified.
- All `.py` source files — these are in-scope and actively used.

---

## Step 3: Verification Protocol (Run BEFORE committing)

### 3.1 Confirm only expected changes
```bash
git status
```
Expected output: Only `routers/__init__.py` deletion and `__pycache__/` removals (if any were tracked).

### 3.2 Verify no import breakage
```bash
cd backend
python -c "from routers.forecast import router; from routers.eda import router; from routers.map import router; from routers.predict import router; from routers.admin import router; from routers.simulate import router; print('All router imports OK')"
```

### 3.3 Verify `__pycache__` is ignored
```bash
git check-ignore -v backend/__pycache__/ backend/core/__pycache__/ backend/routers/__pycache__/
```
All should be matched by `.gitignore` rules.

### 3.4 Verify mount point directories still exist
```bash
Test-Path backend/models_output
Test-Path backend/raw_data
```
Both must return `True`.

### 3.5 Review full diff
```bash
git diff --stat
git diff
```
Confirm no accidental changes to source code.

---

## Step 4: Commit Sequence

1. Stage changes:
   ```bash
   git add -A
   ```

2. Commit:
   ```
   refactor: tidy backend folder — remove empty __init__.py and clean __pycache__ artifacts
   ```

3. Push:
   ```bash
   git push origin feature/connect-backend-frontend
   ```

---

## Summary

| Action | Path | Reason |
|--------|------|--------|
| **DELETE** | `backend/routers/__init__.py` | Empty file, no purpose in Python 3.3+ |
| **DELETE** | `backend/*/__pycache__/` (8 dirs) | Transient cache, already gitignored |
| **KEEP** | `backend/models_output/` | Docker volume mount point |
| **KEEP** | `backend/raw_data/` | Docker volume mount point |
| **KEEP** | All other files/dirs | Active source code, configs, and Docker files |
| **NO CHANGE** | Root `.gitignore` | Already covers `__pycache__/` |
