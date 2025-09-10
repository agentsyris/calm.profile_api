#!/usr/bin/env python3
"""
Test script for Calendly webhook functionality
"""

import requests
import json

# Test webhook endpoint
WEBHOOK_URL = "http://localhost:5000/webhooks/calendly"

# Sample Calendly webhook payload for 15-min intro call
test_payload = {
    "event": "invitee.created",
    "payload": {
        "invitee": {"email": "test@example.com", "name": "Test User"},
        "event_type": {"name": "intro", "slug": "intro"},
        "event": {
            "start_time": "2024-01-15T10:00:00.000000Z",
            "end_time": "2024-01-15T10:15:00.000000Z",
        },
    },
}


def test_calendly_webhook():
    """Test the Calendly webhook endpoint"""
    print("Testing Calendly webhook...")

    try:
        response = requests.post(
            WEBHOOK_URL, json=test_payload, headers={"Content-Type": "application/json"}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 200:
            print("✅ Webhook test successful!")
        else:
            print("❌ Webhook test failed!")

    except Exception as e:
        print(f"❌ Error testing webhook: {e}")


def test_non_intro_call():
    """Test webhook with non-intro call event"""
    print("\nTesting non-intro call event...")

    test_payload_30min = {
        "event": "invitee.created",
        "payload": {
            "invitee": {"email": "test@example.com", "name": "Test User"},
            "event_type": {"name": "30-min debrief call", "slug": "30min"},
        },
    }

    try:
        response = requests.post(
            WEBHOOK_URL,
            json=test_payload_30min,
            headers={"Content-Type": "application/json"},
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 200:
            print("✅ Non-intro call test successful (should not send email)")
        else:
            print("❌ Non-intro call test failed!")

    except Exception as e:
        print(f"❌ Error testing non-intro call: {e}")


if __name__ == "__main__":
    print("Calendly Webhook Test Suite")
    print("=" * 40)

    test_calendly_webhook()
    test_non_intro_call()

    print("\nTest completed!")
