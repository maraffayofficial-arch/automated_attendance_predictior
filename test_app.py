"""
Attendance Predictor — Full API Test & Seed Script
Run from any terminal:  python test_app.py
Requires: pip install requests
"""

import requests
import json
import sys

BASE = "http://localhost:5000/api"
PASS = "\033[92m  PASS\033[0m"
FAIL = "\033[91m  FAIL\033[0m"
INFO = "\033[94m  INFO\033[0m"

token = None
results = {"passed": 0, "failed": 0}


def check(label, condition, detail=""):
    if condition:
        print(f"{PASS}  {label}")
        results["passed"] += 1
    else:
        print(f"{FAIL}  {label}  →  {detail}")
        results["failed"] += 1
    return condition


def headers():
    return {"Authorization": f"Bearer {token}"}


def section(title):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")


# ── 1. Health ─────────────────────────────────────────────
section("1. Health Check")
try:
    r = requests.get(f"{BASE}/health", timeout=5)
    check("Flask is running", r.status_code == 200, r.text)
    check("MongoDB connected", "ok" in r.json().get("status", ""), r.text)
except Exception as e:
    print(f"{FAIL}  Cannot reach Flask at {BASE}")
    print(f"       Error: {e}")
    print("\n  ⚠  Make sure Flask is running:  python backend/app.py")
    sys.exit(1)


# ── 2. Auth ───────────────────────────────────────────────
section("2. Authentication")

# Register admin (may already exist — that's fine)
r = requests.post(f"{BASE}/auth/register", json={
    "username": "admin",
    "password": "admin123",
    "role": "admin"
})
if r.status_code == 201:
    print(f"{INFO}  Admin user created")
elif r.status_code == 409:
    print(f"{INFO}  Admin user already exists")
else:
    print(f"{FAIL}  Register unexpected: {r.status_code} {r.text}")

# Login
r = requests.post(f"{BASE}/auth/login", json={
    "username": "admin",
    "password": "admin123"
})
check("Login returns token", r.status_code == 200 and "token" in r.json(), r.text)
if r.status_code == 200:
    token = r.json()["token"]

if not token:
    print(f"\n  ⚠  Cannot proceed without a token. Check admin credentials.")
    sys.exit(1)

# Wrong password
r = requests.post(f"{BASE}/auth/login", json={"username": "admin", "password": "wrongpass"})
check("Wrong password → 401", r.status_code == 401, r.text)

# /me endpoint
r = requests.get(f"{BASE}/auth/me", headers=headers())
check("/me returns user info", r.status_code == 200 and r.json().get("username") == "admin", r.text)


# ── 3. Persons ────────────────────────────────────────────
section("3. Persons")

test_persons = [
    {"person_id": "EMP-TEST-01", "name": "Alice Johnson",    "type": "employee", "department": "Engineering", "email": "alice@test.com"},
    {"person_id": "EMP-TEST-02", "name": "Bob Martinez",     "type": "employee", "department": "Sales",       "email": "bob@test.com"},
    {"person_id": "STU-TEST-01", "name": "Carol Williams",   "type": "student",  "department": "CS-2A",       "email": "carol@test.com"},
    {"person_id": "STU-TEST-02", "name": "David Chen",       "type": "student",  "department": "CS-2A",       "email": "david@test.com"},
]

created = 0
for p in test_persons:
    r = requests.post(f"{BASE}/persons/", json=p, headers=headers())
    if r.status_code in (201, 409):
        created += 1
check(f"Persons created/exist ({len(test_persons)})", created == len(test_persons))

# List all
r = requests.get(f"{BASE}/persons/", headers=headers())
check("GET /persons/ returns list", r.status_code == 200 and isinstance(r.json(), list), r.text)
check("At least 4 persons in DB", len(r.json()) >= 4, f"got {len(r.json())}")

# Get single
r = requests.get(f"{BASE}/persons/EMP-TEST-01", headers=headers())
check("GET /persons/EMP-TEST-01 works", r.status_code == 200 and r.json()["name"] == "Alice Johnson", r.text)

# Filter by type
r = requests.get(f"{BASE}/persons/", params={"type": "student"}, headers=headers())
check("Filter by type=student works", r.status_code == 200 and all(p["type"] == "student" for p in r.json()), r.text)

# Search
r = requests.get(f"{BASE}/persons/", params={"search": "Alice"}, headers=headers())
check("Search by name works", r.status_code == 200 and any(p["name"] == "Alice Johnson" for p in r.json()), r.text)

# Duplicate rejection
r = requests.post(f"{BASE}/persons/", json=test_persons[0], headers=headers())
check("Duplicate person_id → 409", r.status_code == 409, r.text)

# Update
r = requests.put(f"{BASE}/persons/EMP-TEST-01", json={"department": "R&D"}, headers=headers())
check("PUT /persons/EMP-TEST-01 updates", r.status_code == 200, r.text)

# Not found
r = requests.get(f"{BASE}/persons/DOES-NOT-EXIST", headers=headers())
check("Non-existent person → 404", r.status_code == 404, r.text)


# ── 4. Attendance Records ─────────────────────────────────
section("4. Attendance Records")

test_records = [
    {"person_id": "EMP-TEST-01", "date": "2026-01-02", "attendance_binary": 1, "is_exam_period": 0},
    {"person_id": "EMP-TEST-01", "date": "2026-01-03", "attendance_binary": 0, "is_exam_period": 0},
    {"person_id": "EMP-TEST-01", "date": "2026-01-04", "attendance_binary": 0, "is_exam_period": 0},
    {"person_id": "EMP-TEST-01", "date": "2026-01-05", "attendance_binary": 1, "is_exam_period": 1},
    {"person_id": "EMP-TEST-01", "date": "2026-01-06", "attendance_binary": 0, "is_exam_period": 1},
    {"person_id": "STU-TEST-01", "date": "2026-01-02", "attendance_binary": 1, "is_exam_period": 0},
    {"person_id": "STU-TEST-01", "date": "2026-01-03", "attendance_binary": 1, "is_exam_period": 0},
    {"person_id": "STU-TEST-02", "date": "2026-01-02", "attendance_binary": 0, "is_exam_period": 0},
]

added = 0
for rec in test_records:
    r = requests.post(f"{BASE}/attendance/", json=rec, headers=headers())
    if r.status_code in (201, 409):
        added += 1
check(f"Attendance records added/exist ({len(test_records)})", added == len(test_records))

# Get by person
r = requests.get(f"{BASE}/attendance/", params={"person_id": "EMP-TEST-01"}, headers=headers())
check("GET attendance by person_id", r.status_code == 200 and len(r.json()) >= 5, r.text)

# Get all (for ML retraining)
r = requests.get(f"{BASE}/attendance/all", headers=headers())
check("GET /attendance/all returns records", r.status_code == 200 and len(r.json()) >= 8, r.text)

# Duplicate date rejection
r = requests.post(f"{BASE}/attendance/", json=test_records[0], headers=headers())
check("Duplicate date → 409", r.status_code == 409, r.text)

# Invalid attendance_binary
r = requests.post(f"{BASE}/attendance/", json={
    "person_id": "EMP-TEST-01", "date": "2026-02-01", "attendance_binary": 5
}, headers=headers())
check("Invalid attendance_binary → 400", r.status_code == 400, r.text)


# ── 5. Alerts ─────────────────────────────────────────────
section("5. Alerts — Import Existing Report")

# Import existing alert_report.json (ML team already generated this)
r = requests.post(f"{BASE}/alerts/import", headers=headers())
if r.status_code == 200:
    check("Import alert_report.json works", True)
    data = r.json()
    print(f"{INFO}  Summary: {data.get('summary')}")
elif r.status_code == 404:
    print(f"{INFO}  alert_report.json not found — skipping import (run ML pipeline first)")
else:
    check("Import alert_report.json", False, f"{r.status_code} {r.text}")

# Get latest alerts
r = requests.get(f"{BASE}/alerts/", headers=headers())
if r.status_code == 200:
    check("GET /alerts/ returns data", True)
    alerts = r.json().get("alerts", [])
    print(f"{INFO}  Total alerts: {len(alerts)}")

    # Filter by level
    r2 = requests.get(f"{BASE}/alerts/", params={"level": "CRITICAL"}, headers=headers())
    check("Filter alerts by CRITICAL level", r2.status_code == 200, r2.text)
    crits = r2.json().get("alerts", [])
    print(f"{INFO}  Critical alerts: {len(crits)}")

    # Person-specific alert
    if alerts:
        pid = alerts[0]["person_id"]
        r3 = requests.get(f"{BASE}/alerts/person/{pid}", headers=headers())
        check(f"GET /alerts/person/{pid}", r3.status_code == 200, r3.text)
else:
    print(f"{INFO}  No alert data yet — import a report or run the pipeline")

# History
r = requests.get(f"{BASE}/alerts/history", headers=headers())
check("GET /alerts/history works", r.status_code == 200, r.text)


# ── 6. Auth guard ─────────────────────────────────────────
section("6. Auth Guard (no token should fail)")

for url in ["/persons/", "/attendance/", "/alerts/"]:
    r = requests.get(f"{BASE}{url}")
    check(f"GET {url} without token → 401", r.status_code == 401, f"got {r.status_code}")


# ── Summary ───────────────────────────────────────────────
section("RESULTS")
total = results["passed"] + results["failed"]
print(f"  Passed:  {results['passed']} / {total}")
print(f"  Failed:  {results['failed']} / {total}")

if results["failed"] == 0:
    print("\n  \033[92m✓ All tests passed! The backend is working correctly.\033[0m")
    print("  Now open http://localhost:5173 and log in with admin / admin123\n")
else:
    print(f"\n  \033[91m✗ {results['failed']} test(s) failed — check the errors above.\033[0m\n")
    sys.exit(1)
