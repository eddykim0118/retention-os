# Retention OS — Eddy's Task Sheet
## Role: Backend + AI Agent (Person 1)

> You are the critical path. If your API isn't working by lunch, everyone stalls.

---

## What We're Building

An AI **Employee** (not a tool) that:
- Scans 500 SaaS accounts automatically
- Calculates health scores
- Uses Claude AI to analyze at-risk accounts
- **Actually acts**: sends Slack alerts, creates Linear tickets
- Only asks for human approval on high-value accounts ($50K+ ARR)

---

## Your Files

| File | What It Does |
|---|---|
| `backend/main.py` | FastAPI app, startup CSV→SQLite loader, CORS |
| `backend/database.py` | SQLite connection, CSV loader, query helpers |
| `backend/models.py` | Pydantic response models |
| `backend/health_score.py` | Rule-based scoring + autonomy level logic |
| `backend/agent.py` | Claude API with tool_use |
| `backend/actions.py` | Slack webhook (+ Linear as stretch) |
| `backend/routes.py` | 4 API endpoints + SSE streaming |

---

## Step-by-Step Plan

### 9:30-9:45 — Setup

```bash
mkdir retention-os && cd retention-os && git init
mkdir -p backend/data
pip install fastapi uvicorn anthropic aiofiles requests
```

- Copy all 5 CSVs into `backend/data/`
- Create `.env` file (Person 2 will give you the Slack/Linear keys):
```
ANTHROPIC_API_KEY=your-key
SLACK_ALERTS_WEBHOOK=from-person-2
SLACK_URGENT_WEBHOOK=from-person-2
LINEAR_API_KEY=from-person-2
LINEAR_TEAM_ID=from-person-2
```
- Add `.env` to `.gitignore`

### 9:45-10:30 — `database.py` + `main.py`

**database.py:**
- Read all 5 CSVs with `csv.DictReader`
- Create SQLite tables matching each CSV's columns
- Insert all rows
- Create `review_results` table (stores Claude analysis output)
- Create `action_log` table (stores what the AI actually did: slack_sent, linear_created, etc.)
- Write query helper functions

**main.py:**
- FastAPI app with `@app.on_event("startup")` that calls the CSV loader
- CORS middleware allowing `http://localhost:5173`
- Include router from routes.py

**Test:** `uvicorn main:app --reload` → hit `localhost:8000/docs`

### 10:30-11:15 — `health_score.py`

```python
REFERENCE_DATE = "2025-01-01"  # Set to max date in dataset

def calculate_health_score(account_id, db) -> int:
    score = 100

    # 1. Usage drop (last 30d vs previous 30d): -30
    #    JOIN: feature_usage → subscriptions → accounts
    #    If sum(usage_count) dropped > 30%, apply penalty
    if usage_dropped:
        score -= 30

    # 2. Support ticket increase: -20
    if ticket_count_increased:
        score -= 20

    # 3. Escalation flag on any ticket: -15
    if any_escalation:
        score -= 15

    # 4. Downgrade flag on subscription: -20
    if downgrade_flag:
        score -= 20

    # 5. Satisfaction score < 3: -15
    if low_satisfaction:
        score -= 15

    return max(0, score)

def get_autonomy_level(health_score: int, arr_amount: float) -> str:
    """High-risk + high-value = needs approval, everything else = auto"""
    if health_score < 40 and arr_amount >= 50000:
        return "needs_approval"
    return "auto"
```

**IMPORTANT:** feature_usage links to `subscription_id`, NOT `account_id`. You must JOIN through subscriptions to get to accounts. Person 2 is writing these SQL queries for you — ask for them.

### 11:15-12:00 — `routes.py` GET endpoints

```python
@router.get("/api/accounts")
# Return all accounts with health scores, risk levels, action status

@router.get("/api/accounts/{account_id}")
# Return single account with full detail + actions_taken array
```

**Test both in browser.** Then **git push** so Person 2 and 3 can pull.

### 12:00-12:30 — LUNCH

### 12:30-13:15 — `agent.py` (Claude API)

```python
import anthropic
client = anthropic.Anthropic()

tools = [{
    "name": "submit_analysis",
    "description": "Submit churn risk analysis and recommended action",
    "input_schema": {
        "type": "object",
        "properties": {
            "churn_risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "risk_reasons": {"type": "array", "items": {"type": "string"}},
            "next_best_action": {
                "type": "string",
                "enum": ["training_call", "support_escalation",
                         "finance_reminder", "senior_outreach"]
            },
            "action_reasoning": {"type": "string"},
            "why_not_others": {"type": "string"},
            "generated_email": {"type": "string"},
            "internal_memo": {"type": "string"},
            "slack_message": {"type": "string"},
            "urgency_deadline": {"type": "string"}
        },
        "required": ["churn_risk_score", "risk_reasons", "next_best_action",
                     "action_reasoning", "why_not_others",
                     "generated_email", "internal_memo",
                     "slack_message", "urgency_deadline"]
    }
}]

def analyze_account(account_signals: dict) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1500,
        system="""You are an AI Account Manager employee (not an assistant — you ACT).
Analyze customer signals and decide what to do. Use the submit_analysis tool.
Be specific and business-focused.
Explain why you chose this action AND why you rejected alternatives.
Write a ready-to-send Slack message for the CS team.
Set a clear urgency deadline.""",
        tools=tools,
        messages=[{"role": "user", "content": f"Analyze this account:\n{json.dumps(account_signals)}"}]
    )
    # Extract tool_use result from response
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    return None
```

Test with one account manually before wiring up the full flow.

### 13:15-13:45 — `actions.py` (Slack + Linear)

```python
import requests, os

def send_slack_alert(channel_type: str, message: str) -> bool:
    """channel_type: 'alerts' or 'urgent'"""
    webhook = os.environ.get(
        "SLACK_URGENT_WEBHOOK" if channel_type == "urgent" else "SLACK_ALERTS_WEBHOOK"
    )
    if not webhook:
        print(f"[MOCK] Slack {channel_type}: {message}")
        return False
    resp = requests.post(webhook, json={"text": message})
    return resp.status_code == 200

def create_linear_ticket(title: str, description: str, priority: int = 2) -> dict:
    """priority: 1=urgent, 2=high, 3=medium"""
    api_key = os.environ.get("LINEAR_API_KEY")
    team_id = os.environ.get("LINEAR_TEAM_ID")
    if not api_key:
        print(f"[MOCK] Linear ticket: {title}")
        return {"mock": True}
    resp = requests.post(
        "https://api.linear.app/graphql",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        json={"query": """
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue { id identifier url }
                }
            }
        """, "variables": {"input": {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority
        }}}
    )
    return resp.json()
```

Notice the fallback: if env vars aren't set, it prints to console instead of crashing. This way you can test without Slack/Linear being ready.

### 13:45-14:30 — `GET /api/review/run` + SSE + approve

> **IMPORTANT: Must be GET, not POST.** Browser's `EventSource` API only supports GET.
> **Use FastAPI native SSE:** `from fastapi.sse import EventSourceResponse` (no sse-starlette needed)

This is the big one. The full agent flow:

```python
from fastapi.sse import EventSourceResponse

@router.get("/api/review/run")
async def run_review():
    async def event_stream():
        # 1. Scan all accounts
        yield sse_event("progress", "Scanning 500 accounts...")
        accounts = get_all_accounts(db)

        # 2. Calculate health scores, pick worst
        yield sse_event("progress", f"Found {len(at_risk)} at-risk accounts")

        # 3. For each at-risk account:
        for i, account in enumerate(top_at_risk):
            yield sse_event("analyzing", account["account_name"], i+1, len(top_at_risk))

            # Claude analysis
            analysis = analyze_account(build_signals(account))

            # Determine autonomy level
            level = get_autonomy_level(account["health_score"], account["arr_amount"])

            if level == "auto":
                # Auto-execute: send Slack alert
                send_slack_alert("alerts", analysis["slack_message"])
                yield sse_event("action", f"Sent Slack alert for {account['account_name']}")
            else:
                # Needs approval: notify urgent channel
                send_slack_alert("urgent", f"NEEDS APPROVAL: {analysis['slack_message']}")
                yield sse_event("action", f"{account['account_name']} needs approval — ${account['arr_amount']} ARR")

            # Save to SQLite
            save_review_result(db, account, analysis, level)

        yield sse_event("complete", auto_count, approval_count)

    return EventSourceResponse(event_stream())

@router.post("/api/accounts/{account_id}/approve")
async def approve_action(account_id: str):
    # Load the saved analysis
    # Execute: send Slack #urgent
    # Update status to "approved"
    # Return actions_executed
```

### 14:30-submission — Full flow testing
- Run all 3 scenarios end-to-end
- Verify Slack messages actually arrive
- Verify Linear tickets actually get created
- Fix bugs

---

## 3 Demo Scenarios (Expected Results)

| Account | Health Score | Autonomy | Expected Action | What AI Does |
|---|---|---|---|---|
| Nimbus Analytics | ~35 | auto (ARR $36K) | training_call | Slack alert auto-sent (no approval needed) |
| Vertex Systems | ~65 | auto (ARR $18K) | finance_reminder | Slack alert auto-sent (no approval needed) |
| Orion Global | ~20 | needs_approval (ARR $102K) | senior_outreach | Slack urgent alert → waits for Approve button |

---

## Dependencies on Others

- **From Person 2 (by 10:00):** Slack webhook URLs (Linear keys if time)
- **From Person 2 (by 10:45):** Fixed CSV data + SQL queries for aggregation
- **Person 3 doesn't need anything from you until 12:00** (she works with mock data)

---

## If Running Behind

Priority order (build these first, cut the rest):
1. database.py + health_score.py + GET endpoints (MUST by lunch)
2. agent.py — Claude API call (MUST)
3. actions.py — Slack integration (MUST for "employee" demo)
4. GET /review/run with SSE (MUST — remember: GET not POST!)
5. approve endpoint (MUST for Orion Global demo)
6. Linear integration (stretch — only if everything else works)
