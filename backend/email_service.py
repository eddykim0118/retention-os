"""
Email Service for Retention OS — powered by Claude (Anthropic) + Resend

Flow:
  1. Claude receives account data + ai_summary + suggested_action
  2. Claude decides: should we send an email? if yes, what type?
  3. Claude writes the full personalised email (subject + HTML body)
  4. Resend delivers it to the contact

Email types Claude can choose:
  - promotion    : pricing concern → personalised discount/promo offer
  - overdue      : payment overdue → invoice reminder
  - bug_update   : product bugs/crashes → apology + fix ETA
  - competitor   : evaluating alternatives → retention offer + executive call
  - onboarding   : low adoption → help & resources
  - check_in     : general low health → friendly check-in
  - no_email     : Claude decides no email needed right now
"""

import os
import json
import resend
import anthropic
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "retention-os@resend.dev")

_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))


# ── Claude: decide & write the email ─────────────────────────────────────────

def _claude_generate_email(
    account_name: str,
    contact_email: str,
    health_score: int,
    risk_reason: str,
    arr: int,
    ai_summary: str,
    suggested_action: str,
) -> dict:
    """
    Ask Claude to:
      1. Decide what type of email to send (or no_email)
      2. Write a personalised subject + full HTML email body

    Returns:
      {
        "should_send": bool,
        "email_type": str,
        "subject": str,
        "html": str,
        "reason": str
      }
    """
    discount = "20%" if arr >= 50000 else "15%" if arr >= 20000 else "10%"

    prompt = f"""You are a Customer Success AI for a B2B SaaS company called Retention OS.

A churn risk has been detected. Your job is to:
1. Decide whether to send an email and what TYPE to send.
2. Write a warm, professional, personalised email (subject + HTML body).

── Account Info ──────────────────────────────────
Account Name    : {account_name}
Contact Email   : {contact_email}
Health Score    : {health_score}/100
ARR             : ${arr:,}
Risk Reason     : {risk_reason}
AI Summary      : {ai_summary}
Suggested Action: {suggested_action}
Discount Budget : up to {discount} if needed

── Email Type Options ────────────────────────────
- "promotion"   → customer seems price-sensitive or mentioned cost/pricing → send a personalised discount offer
- "overdue"     → invoice overdue / payment issue → polite payment reminder with help options
- "bug_update"  → product bugs, crashes, broken features → apology + fix ETA
- "competitor"  → evaluating competitors / switching → retention offer + executive call invite
- "onboarding"  → low feature adoption, setup struggles → helpful resources + CSM offer
- "check_in"    → general low health, no specific signal → friendly check-in
- "no_email"    → no email needed right now (too early, already handled, etc.)

── Rules ─────────────────────────────────────────
- Pick the MOST appropriate type based on the risk signals and suggested action.
- If ARR > $50,000, be more personalised and urgent in tone.
- Write as a real CSM: warm, human, not robotic or generic.
- HTML: use <h2>, <p>, <ul>, <li>, <strong> only. Keep it clean.
- Do NOT mention health scores, internal metrics, or "churn risk" in the email.
- Respond ONLY with valid JSON (no extra text, no markdown fences):

{{"should_send": true, "email_type": "promotion", "subject": "A special offer for Acme Corp", "html": "<h2>Hi Acme team,</h2><p>...</p>", "reason": "Customer mentioned pricing is too expensive."}}"""

    message = _claude.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown fences if Claude wraps in ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── Public API ────────────────────────────────────────────────────────────────

async def send_retention_email(
    account_name: str,
    contact_email: str,
    health_score: int,
    risk_reason: str,
    arr: int,
    ai_summary: str,
    suggested_action: str = "",
) -> dict:
    """
    Main entry point.
    Claude decides what email to send and writes it → Resend delivers it.

    Returns:
      {
        "success": bool,
        "should_send": bool,
        "email_type": str,
        "email_id": str,
        "subject": str,
        "reason": str
      }
    """
    print(f"[Email] 🤖 Asking Claude what to send for {account_name}...")

    try:
        decision = _claude_generate_email(
            account_name, contact_email, health_score,
            risk_reason, arr, ai_summary, suggested_action,
        )
    except Exception as e:
        print(f"[Email] ❌ Claude error: {e}")
        return {"success": False, "should_send": False, "email_type": "error"}

    email_type = decision.get("email_type", "no_email")
    reason = decision.get("reason", "")
    print(f"[Email] 🧠 Claude → {email_type}: {reason}")

    if not decision.get("should_send", False) or email_type == "no_email":
        print(f"[Email] ⏭️  No email needed.")
        return {"success": True, "should_send": False, "email_type": email_type, "reason": reason}

    subject = decision.get("subject", f"Important update for {account_name}")
    html = decision.get("html", "")

    if not resend.api_key:
        print("[Email] WARNING: RESEND_API_KEY not set. Skipping send.")
        print(f"[Email] 📧 Would have sent:\n  Subject: {subject}\n  Type: {email_type}")
        return {
            "success": False, "should_send": True,
            "email_type": email_type, "subject": subject, "reason": reason,
        }

    try:
        response = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [contact_email],
            "subject": subject,
            "html": html,
        })
        email_id = response.get("id", "unknown")
        print(f"[Email] ✅ Sent [{email_type}] → {contact_email} (id: {email_id})")
        return {
            "success": True,
            "should_send": True,
            "email_type": email_type,
            "email_id": email_id,
            "subject": subject,
            "reason": reason,
        }

    except Exception as e:
        print(f"[Email] ❌ Resend error: {e}")
        return {"success": False, "should_send": True, "email_type": email_type, "reason": reason}
