#!/usr/bin/env python3
"""
Verify Supabase CRM setup is complete
"""

from pathlib import Path
import json
import sys
import os

def check_file(path, description):
    if Path(path).exists():
        print(f"✅ {description}: Found")
        return True
    else:
        print(f"❌ {description}: Missing ({path})")
        return False

def main():
    print("=" * 50)
    print("SUPABASE CRM SETUP VERIFICATION")
    print("=" * 50)
    print()

    all_ok = True

    # Check environment variables
    print("Checking environment variables...")
    env_vars = {
        "SUPABASE_URL": "Supabase URL",
        "SUPABASE_SERVICE_ROLE_KEY": "Service role key"
    }

    for var, desc in env_vars.items():
        if os.getenv(var):
            print(f"✅ {desc}: Set")
        else:
            print(f"❌ {desc}: Not set (export {var}=...)")
            all_ok = False

    # Check .env file exists (optional but recommended)
    env_file = Path(__file__).parent / "pm-dashboard" / ".env"
    if env_file.exists():
        print(f"✅ .env file found: {env_file}")
    else:
        print(f"⚠️  .env file not found. You can create it from .env.example")

    # Check supabase package
    try:
        from supabase import create_client
        print("✅ supabase package installed")
    except ImportError:
        print("❌ supabase not installed (run: pip install supabase)")
        all_ok = False

    # Test database connection
    if all_ok:
        try:
            from supabase_crm_client import SupabaseCRMClient
            crm = SupabaseCRMClient()
            stats = crm.get_dashboard_stats()
            print("✅ Database connection successful")
            print(f"   Current stats: {stats}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            all_ok = False

    print()
    if all_ok:
        print("✅ All checks passed! Supabase CRM is ready.")
        print()
        print("Next steps:")
        print("1. Make sure you ran the SQL to create tables")
        print("2. Set up Row Level Security policies")
        print("3. Restart the dashboard server")
        print("4. Open http://localhost:8080/crm")
    else:
        print("❌ Setup incomplete. Follow the instructions in SUPABASE_SETUP_GUIDE.md")
        sys.exit(1)

if __name__ == "__main__":
    main()
