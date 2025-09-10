#!/usr/bin/env python3
"""
Simple script to poll Calendly for new intro call bookings.
Run this every 5-10 minutes via cron job or Render cron.
"""

import requests
import os
import sys
from datetime import datetime


def poll_calendly():
    """Poll the Calendly API endpoint"""
    try:
        # Get the backend URL from environment or use default
        backend_url = os.getenv(
            "BACKEND_URL", "https://calm-profile-api-9uhe.onrender.com"
        )

        # Call the polling endpoint
        response = requests.get(f"{backend_url}/api/check-calendly-bookings")

        if response.status_code == 200:
            data = response.json()
            print(f"[{datetime.now()}] ✅ {data['message']}")

            if data.get("new_bookings"):
                for booking in data["new_bookings"]:
                    print(f"  📧 Sent follow-up to: {booking['email']}")
        else:
            print(
                f"[{datetime.now()}] ❌ Error: {response.status_code} - {response.text}"
            )

    except Exception as e:
        print(f"[{datetime.now()}] ❌ Failed to poll Calendly: {str(e)}")


if __name__ == "__main__":
    poll_calendly()
