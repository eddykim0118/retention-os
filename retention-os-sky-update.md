# Retention OS - Sky Update

Date: 2026-03-26
Branch: `Sky`

## Summary

This document summarizes the frontend work completed so far, the setup/runtime issues that were fixed, the current data status, and the next recommended steps.

## What Has Been Completed

### 1. Frontend app scaffolded

A new React + Vite frontend was created under [`frontend/`](/Users/haneulsong/Desktop/retention-os/frontend).

Main files:
- [`frontend/src/App.jsx`](/Users/haneulsong/Desktop/retention-os/frontend/src/App.jsx)
- [`frontend/src/main.jsx`](/Users/haneulsong/Desktop/retention-os/frontend/src/main.jsx)
- [`frontend/vite.config.js`](/Users/haneulsong/Desktop/retention-os/frontend/vite.config.js)
- [`frontend/src/styles.css`](/Users/haneulsong/Desktop/retention-os/frontend/src/styles.css)

### 2. Dashboard UI implemented

The dashboard page was built in:
- [`frontend/src/pages/Dashboard.jsx`](/Users/haneulsong/Desktop/retention-os/frontend/src/pages/Dashboard.jsx)

Implemented features:
- stats cards
- activity feed
- account table
- row click navigation to account detail
- run review button
- API-first loading with mock fallback

### 3. Account detail page implemented

The account detail page was built in:
- [`frontend/src/pages/AccountDetail.jsx`](/Users/haneulsong/Desktop/retention-os/frontend/src/pages/AccountDetail.jsx)

Implemented features:
- risk summary
- recommended action card
- customer email / internal memo / slack message tabs
- approve button for approval-required accounts
- approval state update in UI

### 4. Reusable UI components implemented

Components added:
- [`frontend/src/components/StatsCard.jsx`](/Users/haneulsong/Desktop/retention-os/frontend/src/components/StatsCard.jsx)
- [`frontend/src/components/RiskBadge.jsx`](/Users/haneulsong/Desktop/retention-os/frontend/src/components/RiskBadge.jsx)
- [`frontend/src/components/ActivityFeed.jsx`](/Users/haneulsong/Desktop/retention-os/frontend/src/components/ActivityFeed.jsx)

Notes:
- the placeholder decorative square in `StatsCard` was replaced with real per-card icons
- risk colors and status badges were added

### 5. Mock/API bridge added

Data files:
- [`frontend/src/lib/mockData.js`](/Users/haneulsong/Desktop/retention-os/frontend/src/lib/mockData.js)
- [`frontend/src/lib/api.js`](/Users/haneulsong/Desktop/retention-os/frontend/src/lib/api.js)

Behavior:
- tries real `/api` endpoints first
- falls back to mock data if backend is unavailable
- includes mock scenarios for:
  - Nimbus Analytics
  - Vertex Systems
  - Orion Global

### 6. Root-level npm scripts added

A root [`package.json`](/Users/haneulsong/Desktop/retention-os/package.json) was added so commands can be run from the repository root.

Available commands:
- `npm run dev`
- `npm run build`
- `npm run install:frontend`

### 7. Frontend dependency/runtime issues fixed

Issues resolved:
- `npm run dev` failing at repo root because there was no root `package.json`
- Vite failing to resolve `react` because frontend dependencies were not installed
- Vite/Tailwind CSS pipeline failing to resolve `postcss`

Current frontend dependency file:
- [`frontend/package.json`](/Users/haneulsong/Desktop/retention-os/frontend/package.json)

Important note:
- `postcss` is now included directly in `devDependencies`

## Verification Done

The frontend was validated with production builds from the repo root:

```bash
npm run build
```

This completed successfully after dependency fixes.

## Git History Relevant to Sky Work

Recent commits on `Sky`:
- `1bf17c6` - Add frontend retention dashboard
- `d6dbd1d` - Icon update

## Current Data Status

The local CSV data in [`backend/db/`](/Users/haneulsong/Desktop/retention-os/backend/db) does not yet appear to match the planned demo scenarios.

Current observations:
- [`backend/db/ravenstack_accounts.csv`](/Users/haneulsong/Desktop/retention-os/backend/db/ravenstack_accounts.csv) still contains generic `Company_*` rows
- `Nimbus Analytics`, `Vertex Systems`, `Orion Global` are not present in the local CSVs
- [`backend/db/ravenstack_subscriptions.csv`](/Users/haneulsong/Desktop/retention-os/backend/db/ravenstack_subscriptions.csv) does not have `days_overdue`
- [`backend/db/ravenstack_support_tickets.csv`](/Users/haneulsong/Desktop/retention-os/backend/db/ravenstack_support_tickets.csv) does not have `notes`
- [`backend/db/retention.db`](/Users/haneulsong/Desktop/retention-os/backend/db/retention.db) is currently empty locally

Because of that, the frontend is currently relying on mock fallback behavior for the 3 demo accounts.

## Current Local Working State

At the time this update file was written, local frontend-related changes still exist beyond the pushed UI commits.

Current local items include:
- updated [`frontend/package.json`](/Users/haneulsong/Desktop/retention-os/frontend/package.json)
- updated [`frontend/package-lock.json`](/Users/haneulsong/Desktop/retention-os/frontend/package-lock.json)
- local Vite cache under `frontend/.vite/`

## Recommended Next Steps

### Priority 1. Sync branch with latest main

`origin/main` has moved ahead, but local frontend edits exist, so merge should be done carefully after deciding whether to:
- commit current local changes first
- or stash them temporarily before merging

### Priority 2. Confirm backend contract

Need to verify real backend responses for:
- `GET /api/accounts`
- `GET /api/accounts/:id`
- `POST /api/accounts/:id/approve`
- `GET /api/review/run`

### Priority 3. Update demo data

Need to confirm whether another teammate already updated:
- CSV source files
- backend data loader
- SQLite generation flow

If not, demo accounts and missing fields still need to be added.

### Priority 4. Full-stack integration test

Once backend/data are ready, test:
- dashboard list from real API
- detail page from real API
- approval flow
- SSE activity feed
- mock fallback no longer needed for demo path

## Quick Run Commands

From repo root:

```bash
npm run dev
```

Frontend-only install if needed:

```bash
npm run install:frontend
```

Frontend production build:

```bash
npm run build
```
