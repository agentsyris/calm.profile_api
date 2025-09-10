#!/usr/bin/env python3
"""
Setup script to help configure missing environment variables for the Calm Profile API.
Run this script to check your current configuration and get guidance on missing variables.
"""

import os
from dotenv import load_dotenv


def check_env_vars():
    """Check which environment variables are configured and which are missing."""
    load_dotenv()

    required_vars = {
        "DATABASE_URL": "Database connection string (SQLite for dev, PostgreSQL for prod)",
        "STRIPE_SECRET_KEY": "Stripe secret key for payment processing",
        "STRIPE_WEBHOOK_SECRET": "Stripe webhook secret for payment verification",
        "PRICE_ID": "Stripe price ID for the product/service",
        "FRONTEND_URL": "Frontend URL for CORS and redirects",
    }

    optional_vars = {
        "SECRET_KEY": "Flask secret key (auto-generated if not provided)",
        "PORT": "Port to run the API on (defaults to 5000)",
    }

    print("🔍 Environment Variable Check")
    print("=" * 50)

    missing_required = []
    configured_required = []

    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if "SECRET" in var or "KEY" in var:
                masked_value = (
                    value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                )
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
            configured_required.append(var)
        else:
            print(f"❌ {var}: MISSING - {description}")
            missing_required.append(var)

    print("\n📋 Optional Variables:")
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚪ {var}: Not set - {description}")

    print("\n" + "=" * 50)

    if missing_required:
        print("⚠️  MISSING REQUIRED VARIABLES:")
        for var in missing_required:
            print(f"   - {var}")
        print("\n💡 To fix this, update your .env file with the missing variables.")
        print("   You can get these values from:")
        print("   - Stripe Dashboard: https://dashboard.stripe.com/")
        print("   - Database provider (for DATABASE_URL)")
        return False
    else:
        print("🎉 All required environment variables are configured!")
        return True


if __name__ == "__main__":
    check_env_vars()

