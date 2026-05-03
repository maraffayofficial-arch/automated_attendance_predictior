"""
Import missing persons from attendance records into persons collection.
This fixes the issue where attendance data exists but persons are not registered.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from pymongo import MongoClient
from config import MONGO_URI
from datetime import datetime

def main():
    print("=" * 70)
    print("  IMPORT MISSING PERSONS")
    print("=" * 70)

    client = MongoClient(MONGO_URI)
    db = client.get_database()

    # Get all person IDs from attendance records
    attendance_persons = set(r['person_id'] for r in db.attendance_records.find({}, {'person_id': 1}))

    # Get all person IDs from persons collection
    registered_persons = set(p['person_id'] for p in db.persons.find({}, {'person_id': 1}))

    # Find missing persons
    missing = attendance_persons - registered_persons

    print(f"\nFound {len(missing)} persons with attendance data but not registered")

    if not missing:
        print("\n[OK] All persons are already registered!")
        return

    print("\nImporting missing persons...")
    print("-" * 70)

    imported = 0
    for person_id in sorted(missing):
        # Determine type based on ID prefix
        if person_id.startswith('STU'):
            person_type = 'student'
            name = f"Student {person_id}"
        elif person_id.startswith('EMP'):
            person_type = 'employee'
            name = f"Employee {person_id}"
        elif person_id.startswith('PAK'):
            person_type = 'student'
            name = f"Student {person_id}"
        else:
            person_type = 'employee'
            name = f"Person {person_id}"

        # Get attendance count for info
        attendance_count = db.attendance_records.count_documents({'person_id': person_id})

        # Insert person
        try:
            db.persons.insert_one({
                'person_id': person_id,
                'name': name,
                'type': person_type,
                'department': '',
                'email': '',
                'created_at': datetime.utcnow(),
                'imported_from_attendance': True
            })
            print(f"  [OK] {person_id} ({person_type}, {attendance_count} attendance records)")
            imported += 1
        except Exception as e:
            print(f"  [ERROR] {person_id}: {e}")

    print("\n" + "=" * 70)
    print("  IMPORT COMPLETE")
    print("=" * 70)
    print(f"\nImported: {imported} persons")
    print(f"Total persons now: {db.persons.count_documents({})}")
    print("\n[OK] Now run migrate_predictions.py to analyze these persons")
    print("=" * 70)

if __name__ == "__main__":
    main()
