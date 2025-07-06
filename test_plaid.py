#!/usr/bin/env python3
"""
Test script to verify Plaid integration is working correctly
"""
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_bot.settings')
django.setup()

from core.services.plaid import PlaidService

def test_plaid_connection():
    """Test basic Plaid connection and link token creation"""
    print("🔧 Testing Plaid Integration...")
    print(f"Client ID: {settings.PLAID_CLIENT_ID}")
    print(f"Environment: {settings.PLAID_ENV}")
    print("Secret: [HIDDEN]")
    print()
    
    try:
        # Initialize Plaid service
        plaid_service = PlaidService()
        print("✅ Plaid service initialized successfully")
        
        # Test link token creation
        print("📱 Creating Link token...")
        link_token = plaid_service.create_link_token(user_id="test_user_123")
        
        if link_token:
            print("✅ Link token created successfully!")
            print(f"Token preview: {link_token[:20]}...")
            print()
            print("🎉 Plaid integration is working correctly!")
            print()
            print("Next steps:")
            print("1. Start Django server: python3 manage.py runserver")
            print("2. Login to admin and go to dashboard")
            print("3. You can now connect sandbox bank accounts")
            print()
            print("📋 Sandbox test credentials:")
            print("Username: user_good")
            print("Password: pass_good")
            
        else:
            print("❌ Link token creation failed")
            
    except Exception as e:
        print(f"❌ Error testing Plaid connection: {e}")
        print()
        print("🔍 Troubleshooting:")
        print("- Check your PLAID_CLIENT_ID and PLAID_SECRET in .env")
        print("- Ensure you're using sandbox credentials")
        print("- Verify internet connection")

if __name__ == "__main__":
    test_plaid_connection()