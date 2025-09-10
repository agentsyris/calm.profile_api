#!/usr/bin/env python3
"""
Test script for Calendly API polling approach
"""

import requests
import os
from datetime import datetime


def test_calendly_api():
    """Test the Calendly API polling endpoint"""

    # Test the polling endpoint
    backend_url = "https://calm-profile-api-9uhe.onrender.com"

    print(f"Testing Calendly API polling at: {backend_url}/api/check-calendly-bookings")

    try:
        response = requests.get(f"{backend_url}/api/check-calendly-bookings")

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data['message']}")
        else:
            print(f"❌ Error: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {str(e)}")


if __name__ == "__main__":
    test_calendly_api()
