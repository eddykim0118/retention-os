# Retention OS - Backend

AI Account Manager backend that detects at-risk customers and takes autonomous action.

## Quick Start

```bash
# 1. From project root, activate the virtual environment
source venv/bin/activate

# 2. Start the server
uvicorn backend.main:app --port 8001 --reload
```

The API will be available at `http://localhost:8001`

## Configuration

Create a `.env` file in the `backend/` folder:

```env
# Required for real AI analysis
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Slack webhooks (will mock if not set)
SLACK_ALERTS_WEBHOOK=https://hooks.slack.com/services/...
SLACK_URGENT_WEBHOOK=https://hooks.slack.com/services/...
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/accounts` | List all accounts with health scores |
| GET | `/api/accounts/{id}` | Get account detail |
| GET | `/api/review/run` | Run AI review (SSE stream) |
| POST | `/api/accounts/{id}/approve` | Approve pending action |

## Architecture

```
backend/
├── main.py           # FastAPI app entry point
├── database.py       # SQLite + CSV loader
├── routes.py         # API endpoints
├── health_score.py   # Risk scoring logic
├── agent.py          # Claude AI integration
├── actions.py        # Slack/Linear integrations
├── models.py         # Pydantic models
├── db/               # CSV data + SQLite database
│   ├── retention.db  # Auto-generated on startup
│   └── ravenstack_*.csv
└── tests/            # pytest tests
```

## Database

The SQLite database (`db/retention.db`) is **auto-generated on startup** from the CSV files. Delete it to reset all data.

Tables:
- `accounts` - Customer accounts
- `subscriptions` - Subscription details (MRR, ARR, billing)
- `support_tickets` - Support ticket history
- `feature_usage` - Product usage metrics
- `churn_events` - Historical churn data
- `review_results` - AI analysis results (app-created)
- `action_log` - Actions taken (app-created)

## Demo Accounts

Three demo accounts are pre-configured for testing:

| Account | Health Score | ARR | Autonomy | Risk Signals |
|---------|-------------|-----|----------|--------------|
| Nimbus Analytics | 20 | $36K | auto | Usage -67%, 4 tickets, escalations |
| Vertex Systems | 80 | $18K | auto | Payment 14 days overdue |
| Orion Global | 30 | $102K | **needs_approval** | Tickets, escalations, downgrade flag |

## Running Tests

```bash
source venv/bin/activate
python -m pytest backend/tests/ -v
```

## Toggle Real AI

In `routes.py`, change:
```python
USE_REAL_AI = True  # Default is False (mock mode)
```

## SSE (Server-Sent Events)

The `/api/review/run` endpoint streams real-time updates:

```javascript
const eventSource = new EventSource('http://localhost:8001/api/review/run');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.type: "progress" | "analyzing" | "action" | "complete"
  console.log(data);
};
```

Event types:
- `progress` - General status updates
- `analyzing` - Currently analyzing an account
- `action` - Action taken (slack_sent, needs_approval)
- `complete` - Review finished
