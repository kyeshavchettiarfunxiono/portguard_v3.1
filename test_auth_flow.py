#!/usr/bin/env python3
"""Test authentication flow"""
import requests
import json
import random

BASE_URL = "http://127.0.0.1:8000"


def run_auth_flow() -> None:
    print("=" * 70)
    print("PortGuard CCMS v3 - Authentication Flow Test")
    print("=" * 70)

    # Test 1: Login
    print("\n1️⃣  Testing LOGIN")
    print("-" * 70)

    login_data = {
        "username": "operator@portguard.co.za",
        "password": "Operator123!"
    }

    response = requests.post(
        f"{BASE_URL}/auth/login",
        data=login_data
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print("✅ Login successful!")
        print(f"Token (first 50 chars): {token[:50]}...")
        print(f"Cookies: {response.cookies}")
    else:
        print("❌ Login failed")
        exit(1)

    # Test 2: Access Dashboard with Token in Header
    print("\n2️⃣  Testing DASHBOARD ACCESS (with token in header)")
    print("-" * 70)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(
        f"{BASE_URL}/dashboard",
        headers=headers
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✅ Dashboard accessible with Bearer token!")
        print(f"Response length: {len(response.text)} bytes")
    else:
        print("❌ Dashboard not accessible")
        print(f"Response: {response.text[:200]}")

    # Test 3: Access Dashboard with Cookie
    print("\n3️⃣  Testing DASHBOARD ACCESS (with cookie)")
    print("-" * 70)

    # Create a new session and login to set cookie
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/auth/login",
        data=login_data
    )

    print(f"Login Status: {response.status_code}")
    print(f"Cookies set: {session.cookies}")

    # Now try to access dashboard with the session (which has the cookie)
    response = session.get(f"{BASE_URL}/dashboard")
    print(f"Dashboard Status Code: {response.status_code}")

    if response.status_code == 200:
        print("✅ Dashboard accessible with cookie!")
        print(f"Response length: {len(response.text)} bytes")
    else:
        print("❌ Dashboard not accessible with cookie")
        print(f"Response: {response.text[:200]}")

    # Test 4: Access Operator Dashboard
    print("\n4️⃣  Testing OPERATOR DASHBOARD ACCESS")
    print("-" * 70)

    response = session.get(f"{BASE_URL}/operator-dashboard")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        print("✅ Operator dashboard accessible!")
        print(f"Response length: {len(response.text)} bytes")
    else:
        print("❌ Operator dashboard not accessible")
        print(f"Response: {response.text[:200]}")

    # Test 5: API Stats Endpoint
    print("\n5️⃣  Testing DASHBOARD STATS API")
    print("-" * 70)

    response = session.get(f"{BASE_URL}/api/dashboard-stats")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("✅ Dashboard stats API working!")
        print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print("❌ Dashboard stats API failed")
        print(f"Response: {response.text}")

    # Test 6: Register Container (Requires Booking ID)
    print("\n6️⃣  Testing CONTAINER REGISTRATION")
    print("-" * 70)
    
    # First, get a booking to link to
    bookings_resp = session.get(f"{BASE_URL}/api/bookings/")
    if bookings_resp.status_code == 200 and len(bookings_resp.json()) > 0:
        booking_id = bookings_resp.json()[0]["id"]
        print(f"Found Booking ID: {booking_id}")
        
        # Create container payload
        container_no = f"TEST{random.randint(1000000, 9999999)}"
        
        payload = {
            "container_no": container_no,
            "booking_id": booking_id,
            "type": "20FT"  # Assuming 20FT is valid enum/string
        }
        
        print(f"Attempting to register container: {container_no}")
        
        reg_response = session.post(
            f"{BASE_URL}/api/containers/",
            json=payload
        )
        
        print(f"Status Code: {reg_response.status_code}")
        if reg_response.status_code in [200, 201]:
            print("✅ Container registration successful!")
            print(f"Response: {reg_response.json()}")
        else:
            print("❌ Container registration failed")
            print(f"Response: {reg_response.text}")
            
    else:
        print("⚠️ Could not fetch bookings to test container registration")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    run_auth_flow()
