"""Quick test to verify Slack webhooks are working"""

import sys
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from actions import send_slack_alert

print("Testing Slack integration...\n")

# Test alerts channel
result = send_slack_alert("alerts", "🧪 Test from Retention OS - Alerts channel working!")
print(f"Alerts channel: {'✅ SUCCESS' if result['success'] and not result.get('mock') else '❌ FAILED or MOCK'}")
print(f"  Detail: {result.get('detail')}\n")

# Test urgent channel
result = send_slack_alert("urgent", "🧪 Test from Retention OS - Urgent channel working!")
print(f"Urgent channel: {'✅ SUCCESS' if result['success'] and not result.get('mock') else '❌ FAILED or MOCK'}")
print(f"  Detail: {result.get('detail')}")
