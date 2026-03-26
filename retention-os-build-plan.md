# Retention OS — Verified Build Plan

## What We're Building
An AI Account Manager that detects at-risk SaaS customers, explains why they might churn, and prepares retention actions autonomously. User just clicks "Approve."

**Flow:** DB Scan → Risk Scoring → Claude AI Analysis → Action + Email Draft → Human Approves

---

## Tech Stack
- Backend: FastAPI (Python) + SQLite
- Frontend: React + Vite + Tailwind CSS
- AI: Claude API (claude-sonnet-4-5) with tool_use for structured output
- Real-time: SSE (Server-Sent Events)
- Data: RavenStack dataset (5 CSVs, ~33K rows total)

---

## Critical Data Gaps (MUST Fix Before Building)

The RavenStack CSV data does NOT perfectly match the 3 demo scenarios. These gaps will break the demo if not addressed:

| # | Gap | Why It Breaks | Fix |
|---|---|---|---|
| 1 | Account names are generic ("Company_0", "Company_1") | Demo scenarios need "Nimbus Analytics", "Vertex Systems", "Orion Global" | Insert or rename 3 accounts in the CSV |
| 2 | No invoice/billing overdue data anywhere | Scenario B (Vertex Systems) needs "invoice overdue 14 days" | Add `payment_status` + `days_overdue` columns to subscriptions, or create a small invoices table |
| 3 | No ticket text/notes field | Scenario C (Orion Global) needs "competitor mention in ticket" | Add a `notes` column to support_tickets CSV |
| 4 | `feature_usage` links to `subscription_id`, NOT `account_id` | Health score query needs usage per account but must JOIN through subscriptions | Backend must JOIN: feature_usage → subscriptions → accounts |
| 5 | "Last 30 days" is relative but data spans 2023-2024 | Usage drop calculation will find nothing if using today's date | Set a `REFERENCE_DATE` constant (e.g., max date in dataset) and calculate relative to that |

### Demo Account Data to Prepare

**Scenario A — Product Friction:**
- Account: "Nimbus Analytics" | DevTools | Enterprise
- Subscription: MRR ~$3,000, active, no downgrade
- Feature usage: high usage 6+ weeks ago, drop to ~40% of that in recent 3 weeks
- Support tickets: 4 tickets, priority high/urgent, satisfaction_score 2, some with escalation_flag=True
- No churn event (still active)

**Scenario B — Billing Risk:**
- Account: "Vertex Systems" | FinTech | Pro
- Subscription: MRR ~$1,500, active, healthy usage, `days_overdue=14`
- Feature usage: steady/growing (this is a HEALTHY user with billing issues)
- Support tickets: 0-1 tickets, no escalation
- No churn event

**Scenario C — Enterprise Churn Risk:**
- Account: "Orion Global" | (any industry) | Enterprise
- Subscription: MRR $8,500, ARR $102,000, active
- Feature usage: moderate
- Support tickets: 2+ tickets, satisfaction_score 1-2, notes includes "evaluating competitor solutions"
- No churn event (yet)

---

## Architecture

```
Frontend (React + Vite + Tailwind, port 5173)
├── Dashboard (/)
│   ├── Stats row: Total Accounts | At-Risk | Urgent Renewals | ARR at Risk
│   ├── "Run Daily Review" button
│   ├── SSE progress bar (real-time agent status)
│   └── Account table: Name | Industry | Plan | Risk Score | Urgency | Action
│
└── Account Detail (/account/:id)
    ├── Risk score (large, color-coded: red < 40, yellow 40-70, green > 70)
    ├── Evidence panel (risk signals with icons)
    ├── Next-best-action card (recommendation + reasoning)
    ├── Tabs: Customer Email | Internal Memo
    └── "Approve" button → status changes to "In Progress"

Backend (FastAPI, port 8000)
├── GET /api/review/run     → SSE stream (triggers full agent review)
├── GET  /api/accounts       → list all accounts with scores
├── GET  /api/accounts/:id   → full detail with AI reasoning
└── POST /api/accounts/:id/approve → mark action as "In Progress"

Database: SQLite (loaded from CSVs on startup)
AI: Claude API (claude-sonnet-4-5, tool_use, max_tokens 1500)
```

---

## API Contracts

### GET /api/review/run
Returns SSE stream (`Content-Type: text/event-stream`):
```
data: {"type": "progress", "message": "Scanning 500 accounts..."}
data: {"type": "progress", "message": "Found 12 at-risk accounts"}
data: {"type": "analyzing", "account": "Nimbus Analytics", "index": 1, "total": 3}
data: {"type": "analyzing", "account": "Vertex Systems", "index": 2, "total": 3}
data: {"type": "analyzing", "account": "Orion Global", "index": 3, "total": 3}
data: {"type": "complete", "results_count": 3}
```

### GET /api/accounts
```json
[
  {
    "account_id": "A-NIMBUS",
    "account_name": "Nimbus Analytics",
    "industry": "DevTools",
    "plan_tier": "Enterprise",
    "health_score": 35,
    "risk_level": "high",
    "mrr_amount": 3000,
    "next_best_action": "training_call",
    "status": "pending"
  }
]
```

### GET /api/accounts/:id
```json
{
  "account_id": "A-NIMBUS",
  "account_name": "Nimbus Analytics",
  "industry": "DevTools",
  "plan_tier": "Enterprise",
  "seats": 45,
  "health_score": 35,
  "risk_level": "high",
  "mrr_amount": 3000,
  "arr_amount": 36000,
  "churn_risk_score": 85,
  "risk_reasons": [
    "Usage dropped 60% in 3 weeks",
    "4 unresolved support tickets",
    "2 tickets escalated",
    "Satisfaction score: 2/5"
  ],
  "next_best_action": "training_call",
  "action_reasoning": "Customer shows strong product friction signals. A training call addresses root cause (they may not know how to use key features) while support escalation handles immediate ticket backlog.",
  "generated_email": "Subject: We want to help — dedicated training session for your team\n\nDear Nimbus Analytics team,\n\nWe noticed your team might be running into some friction with [product]. We'd love to set up a dedicated training session...",
  "internal_memo": "PRIORITY: HIGH\nAccount: Nimbus Analytics (Enterprise, $3K MRR)\nRisk: Product friction — usage down 60%, 4 unresolved tickets\nAction: Schedule training call within 48hrs. Escalate open tickets to Tier 2.\nOwner: [Assign CSM]",
  "status": "pending"
}
```

### POST /api/accounts/:id/approve
```json
{"status": "in_progress", "approved_at": "2025-01-15T10:30:00Z"}
```

---

## Health Score Logic

```python
def calculate_health_score(account_id) -> int:
    score = 100

    # 1. Usage drop in recent period vs previous period: -30
    # JOIN feature_usage → subscriptions → accounts
    # Compare sum(usage_count) in last 30 days vs previous 30 days
    # If dropped > 30%, apply penalty
    if usage_dropped_significantly:
        score -= 30

    # 2. Support ticket increase: -20
    # Count tickets in last 30 days vs previous 30 days
    if ticket_count_increased:
        score -= 20

    # 3. Any escalation flag: -15
    if any_ticket_has_escalation:
        score -= 15

    # 4. Downgrade flag on subscription: -20
    if subscription_has_downgrade:
        score -= 20

    # 5. Satisfaction score < 3 on any recent ticket: -15
    if any_satisfaction_below_3:
        score -= 15

    return max(0, score)
```

**IMPORTANT:** Use a `REFERENCE_DATE` constant (max date in dataset) instead of `datetime.now()` since data is from 2023-2024.

---

## Claude API Integration

```python
import anthropic

client = anthropic.Anthropic()

# Use tool_use to enforce structured output
tools = [{
    "name": "submit_analysis",
    "description": "Submit the churn risk analysis for an account",
    "input_schema": {
        "type": "object",
        "properties": {
            "churn_risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "risk_reasons": {"type": "array", "items": {"type": "string"}},
            "next_best_action": {
                "type": "string",
                "enum": ["training_call", "support_escalation", "finance_reminder", "senior_outreach"]
            },
            "action_reasoning": {"type": "string"},
            "generated_email": {"type": "string"},
            "internal_memo": {"type": "string"}
        },
        "required": ["churn_risk_score", "risk_reasons", "next_best_action",
                     "action_reasoning", "generated_email", "internal_memo"]
    }
}]

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1500,
    system="You are an AI Account Manager. Analyze the provided customer signals and return your analysis using the submit_analysis tool. Be specific and business-focused.",
    tools=tools,
    messages=[{
        "role": "user",
        "content": f"Analyze this account:\n{account_signals_json}"
    }]
)
```

---

## Role Assignments

### Person 1 — Backend + Agent (strongest at structure)
**Files:**
- `backend/main.py` — FastAPI app, startup CSV→SQLite, CORS middleware
- `backend/database.py` — SQLite connection, CSV loader, query helpers
- `backend/models.py` — Pydantic response models
- `backend/health_score.py` — Rule-based scoring with REFERENCE_DATE
- `backend/agent.py` — Claude API calls with tool_use
- `backend/routes.py` — All 4 API endpoints including SSE streaming

**Key decisions:**
- Use `sqlite3` directly (no ORM needed for this scale)
- Store Claude analysis results in a `review_results` SQLite table
- SSE via `EventSourceResponse` from `fastapi.sse` (built-in, no extra package needed)
- **Must be GET endpoint** — browser EventSource only supports GET

### Person 2 — Data + SSE + Glue (ok at everything)
**Tasks:**
- Prepare the 3 demo accounts (modify CSVs or write SQL INSERT scripts)
- Add missing columns (`days_overdue`, ticket `notes`)
- Wire SSE: `EventSource` on frontend connecting to `/api/review/run`
- Write the SQL aggregation queries (usage trends, ticket counts)
- Integration testing and bug fixes

### Person 3 — Frontend UI (good at design)
**Files:**
- `frontend/src/App.jsx` — React Router setup (2 routes)
- `frontend/src/pages/Dashboard.jsx` — Main page with everything
- `frontend/src/pages/AccountDetail.jsx` — Detail page
- `frontend/src/components/StatsCard.jsx` — Reusable stat display
- `frontend/src/components/RiskBadge.jsx` — Color-coded risk indicator

**Design notes:**
- Risk colors: red (score < 40), yellow (40-70), green (> 70)
- Use Tailwind's built-in colors, no custom theme needed
- SSE progress: simple progress bar with text status below it
- Account table: sortable by risk score would be nice but not required

---

## Timeline (4.5 hours, ending at 4:00 PM)

| Time | Person 1 (Backend) | Person 2 (Data/Glue) | Person 3 (Frontend) |
|---|---|---|---|
| 9:30-10:00 | `pip install fastapi uvicorn anthropic`, scaffold `backend/` | Finalize demo CSVs with all fixes | `npm create vite@latest`, install tailwind + react-router |
| 10:00-12:00 | `database.py` + `health_score.py` + GET endpoints | SQL queries for aggregation + SSE backend helper | Dashboard page + Account Detail page (use mock data) |
| 12:00-12:30 | Lunch | Lunch | Lunch |
| 12:30-14:00 | `agent.py` (Claude API) + `POST /review/run` with SSE | Connect SSE to frontend + debug data flow | Email/memo tabs + approve button + SSE progress bar |
| 14:00-15:00 | End-to-end test: all 3 scenarios | Integration bug fixes | UI polish + responsive |
| 15:00-15:30 | Bug kill | Bug kill | Bug kill |
| 15:30-16:00 | Demo rehearsal (run all 3 scenarios) | Demo rehearsal | Demo rehearsal |

---

## Folder Structure

```
retention-os/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── health_score.py
│   ├── agent.py
│   ├── routes.py
│   ├── requirements.txt
│   └── data/
│       ├── ravenstack_accounts.csv
│       ├── ravenstack_subscriptions.csv
│       ├── ravenstack_support_tickets.csv
│       ├── ravenstack_feature_usage.csv
│       └── ravenstack_churn_events.csv
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   └── AccountDetail.jsx
│       └── components/
│           ├── StatsCard.jsx
│           └── RiskBadge.jsx
└── README.md
```

---

## Pre-Build Checklist (Tonight)

- [ ] Claude API key works — test: `curl https://api.anthropic.com/v1/messages` with claude-sonnet-4-5
- [ ] 3 demo accounts data prepared (CSVs modified or SQL INSERTs ready)
- [ ] Missing columns added (days_overdue, ticket notes)
- [ ] Share this plan + API contracts with team
- [ ] Create git repo with folder structure
- [ ] Agree: backend port 8000, frontend port 5173

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Claude API rate limits during demo | Cache results in SQLite `review_results` table; only call Claude for new/unanalyzed accounts |
| SSE doesn't connect | Fallback: frontend polls GET /api/accounts every 2 seconds |
| Demo scenario data doesn't trigger right scores | Pre-seed exact data; hardcode REFERENCE_DATE to match data dates |
| Claude returns unexpected format | tool_use enforces the JSON schema — this is why we use it |
| Someone's code breaks integration | Person 2 (glue role) is specifically assigned to debug this |
