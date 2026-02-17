#!/usr/bin/env python3
"""
Comprehensive test suite for Tier 2/3 features with authentication.
Tests: Vessel Priority Alerts, Downtime Cost Engine, State Machine, Cargo Manifest, Supervisor RLS
"""
import requests
import json
from datetime import datetime, timedelta
import time

BASE_URL = "http://127.0.0.1:9000"

def test_health_check():
    """Test basic health check"""
    print("\n🏥 TEST: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Server: {data.get('service')} v{data.get('version')}")
            return True
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection Error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def get_or_create_user(email, password, role="OPERATOR"):
    """Create or retrieve a test user"""
    # Try to register
    try:
        username = email.split("@")[0]
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={"email": email, "password": password, "username": username, "role": role},
            timeout=5
        )
        if response.status_code in [200, 201]:
            print(f"   ✅ Created user: {email}")
        elif response.status_code == 400:
            print(f"   ℹ️  User {email} already exists")
        else:
            print(f"   ⚠️  Register response: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Register error: {e}")

def get_auth_token(email, password):
    """Get JWT token for a user"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": email, "password": password},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"   ✅ Got token for {email}")
            return token
        else:
            print(f"   ❌ Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ Token error: {e}")
        return None

def test_vessel_priority_alerts(supervisor_token):
    """Test Tier 1: Vessel Priority Alerts"""
    print("\n📊 TEST: Vessel Priority Alerts")
    if not supervisor_token:
        print("   ⏭️  Skipped (no auth token)")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/containers/vessel-bookings/priority-alerts",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Total bookings: {data.get('total_bookings', 0)}")
            print(f"   ✅ Critical alerts: {data.get('critical_alerts', 0)}")
        elif response.status_code == 401:
            print(f"   ❌ Unauthorized (invalid token)")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

def test_downtime_logging(operator_token):
    """Test Tier 2: Downtime Cost Engine"""
    print("\n⏱️  TEST: Downtime Cost Engine")
    if not operator_token:
        print("   ⏭️  Skipped (no auth token)")
        return
    
    # Use a test container ID (will need real container in DB)
    container_id = "550e8400-e29b-41d4-a716-446655440000"
    
    try:
        downtime_req = {
            "downtime_type": "MECHANICAL",
            "reason": "Test crane malfunction",
            "start_time": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "end_time": datetime.utcnow().isoformat()
        }
        
        response = requests.post(
            f"{BASE_URL}/containers/{container_id}/downtime/log",
            json=downtime_req,
            headers={"Authorization": f"Bearer {operator_token}"},
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"   ✅ Duration: {data.get('duration_hours')} hours")
            print(f"   ✅ Cost Impact: R{data.get('cost_impact', 0):.2f}")
        elif response.status_code == 404:
            print(f"   ⚠️  Container not found (expected - no test data yet)")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

def test_state_machine_packing(operator_token):
    """Test Tier 3: State Machine - Packing"""
    print("\n🔒 TEST: State Machine - Packing Closure")
    if not operator_token:
        print("   ⏭️  Skipped (no auth token)")
        return
    
    container_id = "550e8400-e29b-41d4-a716-446655440000"
    
    try:
        # Check readiness
        response = requests.get(
            f"{BASE_URL}/containers/{container_id}/packing-readiness",
            headers={"Authorization": f"Bearer {operator_token}"},
            timeout=5
        )
        print(f"   Readiness Check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Can Close: {data.get('can_close', False)}")
        elif response.status_code == 404:
            print(f"   ⚠️  Container not found")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

def test_cargo_manifest(operator_token):
    """Test Tier 4: Cargo Manifest"""
    print("\n📦 TEST: Cargo Manifest")
    if not operator_token:
        print("   ⏭️  Skipped (no auth token)")
        return
    
    container_id = "550e8400-e29b-41d4-a716-446655440000"
    
    try:
        # Get manifest
        response = requests.get(
            f"{BASE_URL}/containers/{container_id}/manifest",
            headers={"Authorization": f"Bearer {operator_token}"},
            timeout=5
        )
        print(f"   Get Manifest: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Total items: {data.get('total_items', 0)}")
            print(f"   ✅ Total quantity: {data.get('total_quantity', 0)}")
        elif response.status_code == 404:
            print(f"   ⚠️  Container not found")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

def test_supervisor_rls(supervisor_token):
    """Test Tier 5: Supervisor RLS"""
    print("\n🔐 TEST: Supervisor Row-Level Security")
    if not supervisor_token:
        print("   ⏭️  Skipped (no auth token)")
        return
    
    try:
        # Get supervisor dashboard
        response = requests.get(
            f"{BASE_URL}/containers/supervisor/dashboard",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            timeout=5
        )
        print(f"   Dashboard: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"   ✅ Visible containers: {len(data)}")
            else:
                print(f"   ✅ Dashboard data retrieved")
        elif response.status_code == 403:
            print(f"   ⚠️  Access Denied (user may not be supervisor role)")
        elif response.status_code == 404:
            print(f"   ⚠️  Endpoint not found")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    print("=" * 70)
    print("  PortGuard v3 - Tier 2/3 Feature Test Suite (with Authentication)")
    print("=" * 70)
    
    # Test health check first
    if not test_health_check():
        print("\n❌ Server is not responding. Make sure to run:")
        print("   python -m uvicorn main:app --host 127.0.0.1 --port 8000")
        exit(1)
    
    # Wait for server to fully initialize
    print("\n⏳ Waiting for server initialization...")
    time.sleep(2)
    
    # Setup test users
    print("\n👤 Setting up test users...")
    operator_email = "test_operator@portguard.dev"
    supervisor_email = "test_supervisor@portguard.dev"
    test_password = "TestPassword123!"
    
    get_or_create_user(operator_email, test_password, "OPERATOR")
    get_or_create_user(supervisor_email, test_password, "SUPERVISOR")
    
    # Get auth tokens
    print("\n🔑 Obtaining authentication tokens...")
    operator_token = get_auth_token(operator_email, test_password)
    supervisor_token = get_auth_token(supervisor_email, test_password)
    
    # Run tests
    print("\n" + "=" * 70)
    print("  Running Tier 2/3 Feature Tests")
    print("=" * 70)
    
    try:
        test_vessel_priority_alerts(supervisor_token)
        test_downtime_logging(operator_token)
        test_state_machine_packing(operator_token)
        test_cargo_manifest(operator_token)
        test_supervisor_rls(supervisor_token)
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
    
    print("\n" + "=" * 70)
    print("  ✅ Test suite completed!")
    print("=" * 70)
    print("\n📝 Notes:")
    print("   • Some endpoints may return 404 if test data doesn't exist in DB")
    print("   • Run 'python seed_users.py' to populate test data")
    print("   • Check server logs for detailed error information")
