#!/usr/bin/env python3
"""
Comprehensive test suite for Tier 2/3 features.
Tests: Vessel Priority Alerts, Downtime Cost Engine, State Machine, Cargo Manifest, Supervisor RLS
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"

# Test data
SUPERVISOR_TOKEN = "supervisor_token_placeholder"
OPERATOR_TOKEN = "operator_token_placeholder"

def test_vessel_priority_alerts():
    """Test Tier 1: Vessel Priority Alerts"""
    print("\n✅ TEST: Vessel Priority Alerts")
    response = requests.get(
        f"{BASE_URL}/containers/vessel-bookings/priority-alerts",
        headers={"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total bookings: {data.get('total_bookings', 0)}")
        print(f"   Critical alerts: {data.get('critical_alerts', 0)}")
    else:
        print(f"   Error: {response.text}")

def test_downtime_logging():
    """Test Tier 2: Downtime Cost Engine"""
    print("\n✅ TEST: Downtime Cost Engine")
    container_id = "550e8400-e29b-41d4-a716-446655440000"  # Example UUID
    
    downtime_req = {
        "downtime_type": "MECHANICAL",
        "reason": "Crane malfunction",
        "start_time": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "end_time": datetime.utcnow().isoformat()
    }
    
    response = requests.post(
        f"{BASE_URL}/containers/{container_id}/downtime/log",
        json=downtime_req,
        headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"   Duration: {data.get('duration_hours')} hours")
        print(f"   Cost Impact: R{data.get('cost_impact', 0):.2f}")
    else:
        print(f"   Error: {response.text}")

def test_state_machine_packing():
    """Test Tier 3: State Machine - Packing Closure"""
    print("\n✅ TEST: State Machine - Packing Closure")
    container_id = "550e8400-e29b-41d4-a716-446655440000"
    
    # Check readiness
    response = requests.get(
        f"{BASE_URL}/containers/{container_id}/packing-readiness",
        headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"}
    )
    print(f"   Readiness Check Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Can Close: {data.get('can_close', False)}")
        print(f"   Message: {data.get('message', 'N/A')}")
    
    # Attempt close
    response = requests.post(
        f"{BASE_URL}/containers/{container_id}/close-packing",
        headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"}
    )
    print(f"   Close Status: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"   ✅ Closure successful (all photos validated)")
    elif response.status_code == 409:
        print(f"   ⚠️  State machine blocked (missing photos): {response.json().get('detail')}")

def test_cargo_manifest():
    """Test Tier 4: Cargo Manifest"""
    print("\n✅ TEST: Cargo Manifest")
    container_id = "550e8400-e29b-41d4-a716-446655440000"
    
    # Record cargo item
    cargo_req = {
        "description": "Electronics - TV Sets",
        "quantity": 50,
        "unit": "boxes",
        "condition": "GOOD",
        "notes": "All sealed and undamaged"
    }
    
    response = requests.post(
        f"{BASE_URL}/containers/{container_id}/manifest/record-item",
        json=cargo_req,
        headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"}
    )
    print(f"   Record Item Status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"   Cargo ID: {data.get('cargo_id')[:8]}...")
        print(f"   Condition: {data.get('condition')}")
    
    # Get manifest
    response = requests.get(
        f"{BASE_URL}/containers/{container_id}/manifest",
        headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"}
    )
    print(f"   Get Manifest Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total items: {data.get('total_items', 0)}")
        print(f"   Total quantity: {data.get('total_quantity', 0)}")
    
    # Get damage report
    response = requests.get(
        f"{BASE_URL}/containers/{container_id}/manifest/damage-report",
        headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"}
    )
    print(f"   Damage Report Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Problem items: {data.get('problem_items_count', 0)}")
        print(f"   Has issues: {data.get('has_issues', False)}")

def test_supervisor_rls():
    """Test Tier 5: Supervisor RLS"""
    print("\n✅ TEST: Supervisor Row-Level Security")
    
    # Get supervisor dashboard
    response = requests.get(
        f"{BASE_URL}/containers/supervisor/dashboard",
        headers={"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}
    )
    print(f"   Dashboard Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total containers visible: {data.get('total_containers', 0)}")
        print(f"   Pending review count: {data.get('pending_review_count', 0)}")
        print(f"   Needs repair count: {data.get('needs_repair_count', 0)}")
    else:
        print(f"   Error: {response.text}")
    
    # Flag container for repair
    container_id = "550e8400-e29b-41d4-a716-446655440000"
    response = requests.post(
        f"{BASE_URL}/containers/{container_id}/flag-repair",
        params={"repair_reason": "Dent on exterior, needs welding"},
        headers={"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}
    )
    print(f"   Flag Repair Status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"   Flagged: {data.get('flagged_for_repair', False)}")
        print(f"   Reason: {data.get('reason')}")

if __name__ == "__main__":
    print("=" * 60)
    print("  PortGuard v3 - Tier 2/3 Feature Test Suite")
    print("=" * 60)
    
    try:
        test_vessel_priority_alerts()
        test_downtime_logging()
        test_state_machine_packing()
        test_cargo_manifest()
        test_supervisor_rls()
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("  Tests completed!")
    print("=" * 60)
