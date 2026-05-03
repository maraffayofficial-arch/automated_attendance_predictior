"""
Test script for new attendance endpoints
"""
import requests
import json

BASE = "http://localhost:5000/api"

# Login first
print("Logging in...")
r = requests.post(f"{BASE}/auth/login", json={
    "username": "admin",
    "password": "admin123"
})

if r.status_code != 200:
    print(f"❌ Login failed: {r.status_code}")
    print("Make sure the backend is running: cd backend && python app.py")
    exit(1)

token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

print("✓ Login successful\n")

# Test 1: Get today's stats
print("1. Testing GET /attendance/stats/today")
r = requests.get(f"{BASE}/attendance/stats/today", headers=headers)
if r.status_code == 200:
    print(f"✓ Today's stats: {json.dumps(r.json(), indent=2)}\n")
else:
    print(f"❌ Failed: {r.status_code} {r.text}\n")

# Test 2: Get weekly stats
print("2. Testing GET /attendance/stats/weekly")
r = requests.get(f"{BASE}/attendance/stats/weekly", headers=headers)
if r.status_code == 200:
    stats = r.json()
    print(f"✓ Weekly stats: {len(stats)} days of data")
    if stats:
        print(f"   Latest: {stats[0]['date']} - {stats[0]['attendance_rate']}% attendance\n")
else:
    print(f"❌ Failed: {r.status_code} {r.text}\n")

# Test 3: Record daily attendance
print("3. Testing POST /attendance/daily")
test_date = "2026-04-29"
r = requests.post(f"{BASE}/attendance/daily", headers=headers, json={
    "date": test_date,
    "records": [
        {"person_id": "EMP-TEST-01", "attendance_binary": 1},
        {"person_id": "STU-TEST-01", "attendance_binary": 1},
        {"person_id": "STU-TEST-02", "attendance_binary": 0}
    ],
    "is_exam_period": 0
})
if r.status_code == 200:
    print(f"✓ Daily attendance recorded: {json.dumps(r.json(), indent=2)}\n")
else:
    print(f"❌ Failed: {r.status_code} {r.text}\n")

# Test 4: Get attendance by date
print(f"4. Testing GET /attendance/date/{test_date}")
r = requests.get(f"{BASE}/attendance/date/{test_date}", headers=headers)
if r.status_code == 200:
    records = r.json()
    print(f"✓ Found {len(records)} records for {test_date}\n")
else:
    print(f"❌ Failed: {r.status_code} {r.text}\n")

print("✅ All tests completed!")
