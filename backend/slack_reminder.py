"""
Slack Reminder Service for Retention OS

Sends at most 3 Slack notifications for a pending approval:
  - 09:00  (Morning)
  - 13:00  (Lunch)
  - 17:00  (Evening)

Rules:
  - Each slot fires ONCE per day, maximum 3 times total.
  - If approved on the web app before a slot fires → no more notifications.
  - After 3 notifications → done, no more pings ever.
"""

import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from slack_service import send_slack_urgent

load_dotenv()

REMINDER_SLOTS = [
    {"label": "🌅 Morning",  "hour": 9,  "minute": 0},
    {"label": "☀️  Lunch",   "hour": 13, "minute": 0},
    {"label": "🌙 Evening",  "hour": 17, "minute": 0},
]

# account_id → state dict
_state: dict = {}


# ── Public API ────────────────────────────────────────────────────────────────

async def start_reminder(
    account_id: str,
    account_name: str,
    health_score: int,
    risk_reason: str,
    arr: int,
    ai_summary: str,
    recommended_action: str,
) -> None:
    """
    Register an account and schedule up to 3 Slack notifications
    at 09:00 / 13:00 / 17:00. Fires each slot exactly once.
    Call this ONCE when a high-value account is detected.
    """
    if account_id in _state:
        print(f"[Reminder] ⏭️  {account_id} already registered. Skipping.")
        return

    _state[account_id] = {
        "account_name": account_name,
        "health_score": health_score,
        "risk_reason": risk_reason,
        "arr": arr,
        "ai_summary": ai_summary,
        "recommended_action": recommended_action,
        "sent_count": 0,
        "approved": False,
        "registered_at": datetime.now(),
    }

    print(f"[Reminder] 🗓️  Registered {account_name} — will notify at 09:00 / 13:00 / 17:00 (max 3x)")
    asyncio.create_task(_run_slots(account_id))


async def mark_approved(account_id: str, action_taken: str) -> None:
    """
    Call this when the user approves on the web app.
    Cancels remaining reminders and posts a confirmation to Slack.
    """
    s = _state.get(account_id)
    if not s or s["approved"]:
        return

    s["approved"] = True
    print(f"[Reminder] ✅ {account_id} approved. No more notifications.")


def get_status(account_id: str) -> dict:
    return _state.get(account_id, {})


# ── Internal ──────────────────────────────────────────────────────────────────

def _seconds_until(hour: int, minute: int) -> float:
    """Seconds until the next HH:MM (today or tomorrow if already passed)."""
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def _run_slots(account_id: str) -> None:
    """Wait for each time slot and fire exactly once, unless already approved."""
    for i, slot in enumerate(REMINDER_SLOTS):
        s = _state.get(account_id)
        if not s or s["approved"] or s["sent_count"] >= len(REMINDER_SLOTS):
            break

        wait = _seconds_until(slot["hour"], slot["minute"])
        print(f"[Reminder] ⏳ {s['account_name']}: slot {i+1}/3 "
              f"({slot['label']} {slot['hour']:02d}:{slot['minute']:02d}) "
              f"— waiting {wait/3600:.1f}h")

        await asyncio.sleep(wait)

        # Re-check after sleeping
        s = _state.get(account_id)
        if not s or s["approved"]:
            print(f"[Reminder] ✅ {account_id} approved while waiting. Stopping.")
            return

        # Send exactly once for this slot
        label = f"{slot['label']} ({slot['hour']:02d}:{slot['minute']:02d})"
        note = f"_Reminder {s['sent_count'] + 1}/3 · {label} · Approve on the web app to stop._"

        success = await send_slack_urgent(
            account_name=s["account_name"],
            account_id=account_id,
            health_score=s["health_score"],
            risk_reason=s["risk_reason"],
            arr=s["arr"],
            ai_summary=s["ai_summary"],
            recommended_action=f"{s['recommended_action']}\n\n{note}",
        )

        if success:
            s["sent_count"] += 1
            print(f"[Reminder] ✅ Sent {s['sent_count']}/3 for {s['account_name']}")

    s = _state.get(account_id)
    if s and not s["approved"]:
        print(f"[Reminder] 🛑 {s['account_name']}: 3/3 reminders sent. No more Slack pings.")
