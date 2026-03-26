"""
Linear Ticket Service for Retention OS
Creates tickets routed by department based on risk_reason keywords.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

LINEAR_API_KEY = os.getenv("LINEAR_API_KEY", "")
LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID", "")
LINEAR_API_URL = "https://api.linear.app/graphql"


# ── Department rules (same keyword logic as slack_service) ──────────────────

_DEPARTMENT_RULES = [
    (
        ["invoice", "overdue", "payment", "billing", "refund", "charge", "pricing", "discount"],
        "Finance",
        "💰",
        "urgent",   # Linear priority: urgent / high / medium / low
    ),
    (
        ["bug", "crash", "error", "broken", "outage", "degraded", "slow", "timeout",
         "api", "feature", "export", "dashboard", "performance"],
        "Engineering",
        "🛠️",
        "high",
    ),
    (
        ["competitor", "alternative", "evaluating", "switching", "churn", "cancel"],
        "Sales",
        "🤝",
        "urgent",
    ),
    (
        ["onboarding", "training", "workflow", "setup", "adoption", "usage"],
        "Customer Success",
        "🎓",
        "medium",
    ),
]

_PRIORITY_MAP = {"urgent": 1, "high": 2, "medium": 3, "low": 4}


def _infer_department(risk_reason: str) -> tuple[str, str, int]:
    """
    Returns (department_name, emoji, linear_priority_int) from risk_reason.
    Falls back to General / priority 3 (medium).
    """
    lower = risk_reason.lower()
    for keywords, dept, emoji, priority_str in _DEPARTMENT_RULES:
        if any(kw in lower for kw in keywords):
            return dept, emoji, _PRIORITY_MAP[priority_str]
    return "General", "📋", _PRIORITY_MAP["medium"]


def _build_ticket(
    account_name: str,
    account_id: str,
    health_score: int,
    risk_reason: str,
    arr: int,
    ai_summary: str,
    department: str,
    emoji: str,
) -> tuple[str, str]:
    """
    Returns (title, description) customised per department.
    """
    titles = {
        "Finance": f"[Finance] Billing / Payment Issue — {account_name}",
        "Engineering": f"[Engineering] Product Issue Causing Churn Risk — {account_name}",
        "Sales": f"[Sales] Competitor Evaluation Alert — {account_name}",
        "Customer Success": f"[CS] Low Adoption / Onboarding Risk — {account_name}",
        "General": f"[General] Churn Risk Detected — {account_name}",
    }

    descriptions = {
        "Finance": f"""## {emoji} Finance — Billing / Payment Alert

**Account:** {account_name} (`{account_id}`)
**Health Score:** {health_score}/100
**ARR:** ${arr:,}

### Risk Signal
{risk_reason}

### AI Analysis
{ai_summary}

### Suggested Actions
- Confirm outstanding invoice status
- Contact billing contact directly
- Offer payment plan or short extension if needed
- Escalate to Finance lead if no response in 24h
""",
        "Engineering": f"""## {emoji} Engineering — Product Issue Driving Churn

**Account:** {account_name} (`{account_id}`)
**Health Score:** {health_score}/100
**ARR:** ${arr:,}

### Risk Signal
{risk_reason}

### AI Analysis
{ai_summary}

### Suggested Actions
- Reproduce reported bug in staging
- Prioritise fix in current sprint
- Notify account CSM once fix is deployed
- Consider proactive status update to customer
""",
        "Sales": f"""## {emoji} Sales — Competitor Evaluation in Progress

**Account:** {account_name} (`{account_id}`)
**Health Score:** {health_score}/100
**ARR:** ${arr:,}

### Risk Signal
{risk_reason}

### AI Analysis
{ai_summary}

### Suggested Actions
- Schedule executive-level call within 48h
- Prepare competitive battlecard
- Offer strategic discount or additional seats
- Loop in AE + CSM for joint outreach
""",
        "Customer Success": f"""## {emoji} Customer Success — Adoption / Onboarding Risk

**Account:** {account_name} (`{account_id}`)
**Health Score:** {health_score}/100
**ARR:** ${arr:,}

### Risk Signal
{risk_reason}

### AI Analysis
{ai_summary}

### Suggested Actions
- Schedule onboarding review call
- Share relevant help docs / tutorials
- Assign dedicated CSM if not already assigned
- Track feature adoption over next 2 weeks
""",
        "General": f"""## {emoji} Churn Risk — General

**Account:** {account_name} (`{account_id}`)
**Health Score:** {health_score}/100
**ARR:** ${arr:,}

### Risk Signal
{risk_reason}

### AI Analysis
{ai_summary}

### Suggested Actions
- Review account history
- Schedule check-in call
- Identify root cause and assign to correct team
""",
    }

    title = titles.get(department, titles["General"])
    description = descriptions.get(department, descriptions["General"])
    return title, description


# ── Public API ───────────────────────────────────────────────────────────────

async def create_linear_ticket(
    account_name: str,
    account_id: str,
    health_score: int,
    risk_reason: str,
    arr: int,
    ai_summary: str,
) -> dict:
    """
    Create a Linear ticket routed to the correct department team label.
    Returns {"success": bool, "issue_id": str, "issue_url": str, "department": str}
    """
    department, emoji, priority = _infer_department(risk_reason)
    title, description = _build_ticket(
        account_name, account_id, health_score,
        risk_reason, arr, ai_summary, department, emoji,
    )

    if not LINEAR_API_KEY or not LINEAR_TEAM_ID:
        print("[Linear] WARNING: API key or Team ID not set. Skipping.")
        return {"success": False, "department": department}

    mutation = """
    mutation CreateIssue($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue {
          id
          url
          title
        }
      }
    }
    """

    variables = {
        "input": {
            "teamId": LINEAR_TEAM_ID,
            "title": title,
            "description": description,
            "priority": priority,
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                LINEAR_API_URL,
                json={"query": mutation, "variables": variables},
                headers={
                    "Authorization": LINEAR_API_KEY,
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            data = response.json()

            if "errors" in data:
                print(f"[Linear] ❌ GraphQL error: {data['errors']}")
                return {"success": False, "department": department}

            issue = data["data"]["issueCreate"]["issue"]
            print(f"[Linear] ✅ Ticket created — [{department}] {issue['url']}")
            return {
                "success": True,
                "department": department,
                "issue_id": issue["id"],
                "issue_url": issue["url"],
                "title": title,
            }

    except Exception as e:
        print(f"[Linear] ❌ Exception: {e}")
        return {"success": False, "department": department}
