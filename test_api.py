#!/usr/bin/env python3
"""
Test script to verify USC API v5 compatibility.
Tests all three endpoints used by the booking tool.
"""

import requests
import sys
from datetime import datetime, timedelta
from pprint import pprint

# Test configuration (will be replaced with env vars in Phase 2)
BASE_URL = "https://api.urbansportsclub.com/api/v5"
HEADERS = {
    'accept-encoding': 'gzip, deflate',
    'user-agent': 'USCAPP/4.0.8 (android; 28; Scale/2.75)',
    'accept-language': 'en-US;q=1.0',
}

def test_api_version():
    """Test if API v5 base URL is still accessible."""
    print("\n[TEST 1] Testing API base URL accessibility...")
    try:
        # Try a simple endpoint that doesn't require auth
        response = requests.get(f"{BASE_URL}/courses", headers=HEADERS, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 404:
            print("❌ FAIL: API v5 not found - may be deprecated")
            return False
        elif response.status_code in [200, 400, 401]:  # 400/401 acceptable (missing params/auth)
            print("✅ PASS: API v5 endpoint exists")
            return True
        else:
            print(f"⚠️  WARN: Unexpected status {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: {e}")
        return False

def test_courses_endpoint(location_id=15238):
    """Test courses listing endpoint without authentication."""
    print("\n[TEST 2] Testing courses endpoint (no auth required)...")

    target_date = (datetime.today() + timedelta(days=14)).strftime('%Y-%m-%d')
    url = f"{BASE_URL}/courses"
    params = {
        'forDurationOfDays': 1,
        'query': '',
        'pageSize': 10,
        'page': 1,
        'locationId': location_id,
        'startDate': target_date
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")

        if response.status_code == 200:
            data = response.json()
            print("✅ PASS: Courses endpoint working")
            print(f"Response structure: {list(data.keys())}")

            if 'data' in data and 'classes' in data['data']:
                classes = data['data']['classes']
                print(f"Found {len(classes)} classes")
                if classes:
                    sample = classes[0]
                    print(f"Sample class fields: {list(sample.keys())}")
                    print(f"  - Title: {sample.get('title', 'N/A')}")
                    print(f"  - ID: {sample.get('id', 'N/A')}")
                    print(f"  - Bookable: {sample.get('bookable', 'N/A')}")
                    print(f"  - Free spots: {sample.get('freeSpots', 'N/A')}")
                return True
            else:
                print("⚠️  WARN: Unexpected response structure")
                pprint(data)
                return None
        else:
            print(f"❌ FAIL: Status {response.status_code}")
            print(response.text[:500])
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: {e}")
        return False

def test_auth_endpoint_structure():
    """Test auth endpoint returns proper error structure (we expect 401 without credentials)."""
    print("\n[TEST 3] Testing auth endpoint structure...")

    url = f"{BASE_URL}/auth/token"
    data = {
        'username': 'test@example.com',
        'password': 'invalid',
        'client_secret': 'invalid',
        'client_id': 'invalid',
        'grant_type': 'password'
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code in [401, 400]:
            print("✅ PASS: Auth endpoint exists and returns expected error")
            try:
                error_data = response.json()
                print(f"Error response structure: {list(error_data.keys())}")
                return True
            except:
                print("⚠️  WARN: Response not JSON")
                return None
        elif response.status_code == 404:
            print("❌ FAIL: Auth endpoint not found")
            return False
        else:
            print(f"⚠️  WARN: Unexpected status {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("="*60)
    print("USC API v5 Compatibility Test Suite")
    print("="*60)

    results = {
        'API Accessibility': test_api_version(),
        'Courses Endpoint': test_courses_endpoint(),
        'Auth Endpoint': test_auth_endpoint_structure(),
    }

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  WARN"
        print(f"{test_name}: {status}")

    all_passed = all(r is True for r in results.values())
    any_failed = any(r is False for r in results.values())

    print("\n" + "="*60)
    if all_passed:
        print("✅ OUTCOME: All tests passed! API v5 is compatible.")
        print("NEXT STEP: Proceed with Phase 2 (Security & Env Vars)")
        return 0
    elif any_failed:
        print("❌ OUTCOME: Some tests failed. API may have changed.")
        print("ACTION REQUIRED: Investigate API documentation or use network inspector")
        return 1
    else:
        print("⚠️  OUTCOME: Tests inconclusive. Manual verification needed.")
        return 2

if __name__ == "__main__":
    sys.exit(main())
