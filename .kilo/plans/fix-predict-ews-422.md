# Fix: stale EWS prediction caused by hardcoded `month_extracted`

## Goal
Stop the `/api/predict/ews` Simulasi EWS feature from returning identical output after a few uses when only slider values change.

## Root cause
`frontend/app.js:259` hardcodes `month_extracted: 6` in every request body. With identical payloads, browser/network caching and deterministic model inference make the response appear “stuck”.

## Changes
- `frontend/app.js` (line ~259)
  - Change `month_extracted: 6, // Fallback default`
  - To `month_extracted: new Date().getMonth() + 1,`

## Why this is enough for now
- Backend `PredictionRequest` still declares `month_extracted: int`, so the API contract is unchanged.
- No backend changes required.
- Even if the model currently ignores month, sending the real current month guarantees each request is unique and avoids caching artifacts.

## Out of scope (do not touch)
- Gauge threshold logic (frontend threshold issue) — frontend-related, wait for teammate.
- SPA / refresh-to-home behavior — architectural, discuss with teammate first.
- Backend model code or feature selection.
