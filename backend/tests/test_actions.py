"""
test_actions.py - Tests for actions module

Run with: python -m pytest backend/tests/test_actions.py -v
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from actions import (
    send_slack_alert,
    format_slack_alert_message,
    format_slack_approval_message,
    create_linear_ticket,
    format_linear_ticket,
    send_email,
)


class TestSlackMock:
    """Test Slack functions with mock (no webhook configured)."""

    def test_send_alert_returns_mock_when_no_webhook(self):
        """Should return mock result when no webhook is configured."""
        # Ensure no webhook is set
        os.environ.pop("SLACK_ALERTS_WEBHOOK", None)

        result = send_slack_alert("alerts", "Test message")

        assert result["success"] is True
        assert result["mock"] is True

    def test_send_urgent_returns_mock_when_no_webhook(self):
        """Should return mock result for urgent channel too."""
        os.environ.pop("SLACK_URGENT_WEBHOOK", None)

        result = send_slack_alert("urgent", "Urgent test")

        assert result["success"] is True
        assert result["mock"] is True


class TestSlackFormatting:
    """Test Slack message formatting."""

    def test_format_alert_message_high_risk(self):
        """Should format high risk message with correct emoji."""
        message = format_slack_alert_message(
            account_name="Test Corp",
            health_score=35,
            action="training_call",
            reasoning="Usage dropped significantly",
            urgency="Action needed within 48 hours"
        )

        assert "🚨" in message
        assert "HIGH RISK" in message
        assert "Test Corp" in message
        assert "35/100" in message
        assert "Training Call" in message

    def test_format_alert_message_medium_risk(self):
        """Should format medium risk message with warning emoji."""
        message = format_slack_alert_message(
            account_name="Test Corp",
            health_score=55,
            action="finance_reminder",
            reasoning="Invoice overdue",
            urgency="Review within 1 week"
        )

        assert "⚠️" in message
        assert "MEDIUM RISK" in message

    def test_format_approval_message(self):
        """Should format approval message with ARR."""
        message = format_slack_approval_message(
            account_name="Big Enterprise",
            arr_amount=150000,
            action="senior_outreach",
            reasoning="High-value account at risk"
        )

        assert "APPROVAL NEEDED" in message
        assert "Big Enterprise" in message
        assert "$150,000" in message
        assert "Senior Outreach" in message


class TestLinearMock:
    """Test Linear functions with mock (no API key configured)."""

    def test_create_ticket_returns_mock_when_no_api_key(self):
        """Should return mock result when no API key is configured."""
        os.environ.pop("LINEAR_API_KEY", None)
        os.environ.pop("LINEAR_TEAM_ID", None)

        result = create_linear_ticket(
            title="Test ticket",
            description="Test description"
        )

        assert result["success"] is True
        assert result["mock"] is True
        assert "ticket_id" in result


class TestLinearFormatting:
    """Test Linear ticket formatting."""

    def test_format_ticket_title(self):
        """Should format ticket title correctly."""
        title, description = format_linear_ticket(
            account_name="Test Corp",
            health_score=35,
            action="training_call",
            reasoning="Usage dropped",
            risk_reasons=["Reason 1", "Reason 2"],
            urgency="48 hours"
        )

        assert "[Retention]" in title
        assert "Test Corp" in title
        assert "Training Call" in title

    def test_format_ticket_description(self):
        """Should format ticket description with all sections."""
        title, description = format_linear_ticket(
            account_name="Test Corp",
            health_score=35,
            action="training_call",
            reasoning="Usage dropped significantly",
            risk_reasons=["Usage down 60%", "2 escalated tickets"],
            urgency="Action needed within 48 hours"
        )

        assert "## Account Health Alert" in description
        assert "Test Corp" in description
        assert "35/100" in description
        assert "Risk Signals" in description
        assert "- Usage down 60%" in description
        assert "- 2 escalated tickets" in description


class TestEmailMock:
    """Test email sending with mock fallback."""

    def test_send_email_returns_mock_when_no_api_key(self):
        """Should return mock result when Resend credentials are missing."""
        os.environ.pop("RESEND_API_KEY", None)
        os.environ.pop("RESEND_FROM_EMAIL", None)
        os.environ.pop("TEST_EMAIL", None)

        result = send_email(
            account_name="Test Corp",
            email_content="Subject: Hello\n\nThis is a test email.",
        )

        assert result["success"] is True
        assert result["mock"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
