# Repository Folder Hierarchy Restructuring Plan

## Pre-conditions
- Branch: `feature/connect-backend-frontend` (ahead of origin by 18 commits)
- Must complete and verify locally before merging to `origin/main`

---

## Step 1: Audit and Compare with Reference Structure

**Action:** Compare current file tree against the intended structure per `project_context.md` (permitted scope):
- `backend/` ✅ keep all code, configs, scripts
- `frontend/` ✅ keep only core static assets (`app.js`, `index.html`, `nginx.conf`, `style.css`, `agriculture.jpg`)
- Root: ✅ keep `docker-compose.yml`, `docker-compose.frontend.yml`, `.gitignore`, `project_context.md`, `implementation_plan_agriva.md`, `project_assessment.md`

**Findings:**
| Path | Status | Action |
|------|--------|--------|
| `01_dapur_jupyter/` | **OBsolete** — Jupyter research environment, own `.git`, `Dockerfile`, `data/`, `models/`, `notebooks/`. Data/models are mounted into backend via docker-compose.yml. | **REMOVE** |
| `03_ews_frontend/` | **DEPRECATED backup** — contains only `node_modules/` (no source files). Empty scaffold. | **REMOVE** |
| `frontend/package-lock.json` | **Orphan lockfile** — no `package.json` exists. Project uses vanilla JS served by Nginx. | **REMOVE** |
| `frontend/src/main.js` | **Orphan file** — not referenced in `index.html` or `app.js`. | **REMOVE** |
| `.kilo/worktrees/` | Local agent worktree caches. Should never be committed. | **ADD to .gitignore** |
| `.kilo/node_modules/` | Kilo internal deps. Should never be committed. | **ADD to .gitignore** |
| `.kilo/plans/` | Agent plan files (including this one). Should never be committed. | **ADD to .gitignore** |

---

## Step 2: Update `.gitignore`

Add the following patterns to the existing `.gitignore`:

```gitignore
# Jupyter checkpoints
.ipynb_checkpoints/
*/.ipynb_checkpoints/*

# Python cache
__pycache__/
*.pyc

# MLflow logs
mlruns/

# IDE files
.vscode/
.idea/
*.swp
*.swo

# Node modules (frontend and .kilo)
frontend/node_modules/
.kilo/node_modules/

# Agent/tool local state
.kilo/worktrees/
.kilo/plans/
.kilo/commands/
.kilo/agents/

# Environment and secrets
.env
.env.local
*.pem
*.key

# OS artifacts
.DS_Store
Thumbs.db

# Docker volumes (auto-generated on first run)
pg_data/
```

After editing `.gitignore`, run: `git rm -r --cached frontend/node_modules/ 2>$null; git rm --cached .kilo/worktrees/ 2>$null; git rm --cached .kilo/node_modules/ 2>$null; git rm --cached .kilo/plans/ 2>$null` (handle each path that exists in the index).

---

## Step 3: Remove Obsolete Directories and Files

Execute removals in this order:

1. **Remove `03_ews_frontend/`** (safe — no meaningful files)
   ```bash
   rm -rf 03_ews_frontend/
   ```

2. **Remove `01_dapur_jupyter/`** (safe — research-only per scope; data/models are volume-mounted from host and not tracked in git)
   ```bash
   rm -rf 01_dapur_jupyter/
   ```

3. **Remove orphan frontend files**
   ```bash
   rm -rf frontend/src/
   rm -f frontend/package-lock.json
   ```

4. **Clean `.kilo/` tracked artifacts** (ensure worktrees, node_modules, plans are ignored, then remove from working tree if present)
   - Do NOT delete `.kilo/` directory itself (Kilo runtime needs the folder)
   - Only remove contents that are now gitignored: `.kilo/node_modules/`, `.kilo/worktrees/` contents, `.kilo/plans/` (if already committed)

---

## Step 4: Update `docker-compose.yml`

Remove volume mounts that pointed to the now-deleted `01_dapur_jupyter/`:

**Before:**
```yaml
volumes:
  - ./01_dapur_jupyter/data:/app/raw_data:ro
  - ./01_dapur_jupyter/models:/app/models_output:ro
  - ./backend:/app
```

**After:**
```yaml
volumes:
  - ./backend:/app
```

Rationale: The `raw_data` and `models_output` directories inside the container are populated by the ETL seeder and model loader at runtime from the database or codebase paths, not from the deleted Jupyter directory.

---

## Step 5: Verify Structure Completeness

Run these verification commands:

```bash
# Confirm no stale references to removed paths
grep -r "01_dapur_jupyter" . --exclude-dir=.git || echo "CLEAN"
grep -r "03_ews_frontend" . --exclude-dir=.git || echo "CLEAN"
grep -r "src/main" frontend/ || echo "CLEAN"
grep -r "package-lock" frontend/ || echo "CLEAN"
```

```bash
# Show final top-level tree
ls -la
tree -L 2 -I "__pycache__|node_modules|.kilo|.git" . 2>/dev/null || find . -maxdepth 2 -not -path './.git/*' -not -path './.kilo/*' -not -path '*/__pycache__/*' -not -path '*/node_modules/*' | sort
```

**Expected top-level output:**
```
.
├── backend/
├── .git/
├── .gitignore
├── .kilo/
├── docker-compose.yml
├── docker-compose.frontend.yml
├── frontend/
├── implementation_plan_agriva.md
├── project_assessment.md
└── project_context.md
```

**Expected `frontend/` contents:**
```
frontend/
├── agriculture.jpg
├── app.js
├── index.html
├── nginx.conf
└── style.css
```

**Expected `backend/` contents:**
```
backend/
├── core/
├── ml/
├── models.py
├── repositories/
├── routers/
├── schemas/
├── scripts/
├── services/
├── shared.py
└── ...
```
(plus standard Python cache directories `__pycache__/` in subdirectories — these are gitignored)

---

## Step 6: Local Verification Before Merge

1. **Git status must be clean or only show expected modifications**
   ```bash
   git status
   ```
   - Showstoppers: modified files in `01_dapur_jupyter/`, `03_ews_frontend/`, `frontend/src/` still present

2. **Docker compose sanity check** (if Docker is available and running)
   ```bash
   docker compose config
   ```
   - Ensure no broken volume mount paths remain

3. **Confirm branch diff is limited to cleanup**
   ```bash
   git diff origin/main...HEAD --stat
   ```
   - Verify only repository restructuring changes appear (no accidental functional code changes)

4. **Confirm no .gitignore regressions**
   ```bash
   git check-ignore -v frontend/node_modules/ .kilo/worktrees/ backend/__pycache__/ frontend/src/main.js
   ```
   - All paths above should be ignored

---

## Step 7: Commit and Merge Sequence

1. Stage cleanup changes:
   ```bash
   git add -A
   ```

2. Commit with message:
   ```
   refactor: restructure repository, remove obsolete directories and orphan files
   ```

3. Push to remote (force-with-lease not needed — this is a new commit ahead of origin):
   ```bash
   git push origin feature/connect-backend-frontend
   ```

4. Open PR via GitHub CLI:
   ```bash
   gh pr create --base main --head feature/connect-backend-frontend --title "refactor: clean repository structure and remove obsolete directories"
   ```

5. After CI and review pass, merge to `main` and tag release.

---

## Summary of Changes

| Action | Paths |
|--------|-------|
| **DELETE** | `01_dapur_jupyter/`, `03_ews_frontend/`, `frontend/src/`, `frontend/package-lock.json` |
| **UPDATE** | `.gitignore` (add comprehensive ignore rules) |
| **UPDATE** | `docker-compose.yml` (remove stale volume mounts) |
| **KEEP** | `backend/`, `frontend/` core assets, root docs, compose files, `.kilo/` directory |
