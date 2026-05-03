"""
Migration script to populate person_predictions collection.
Run this once after implementing the real-time ML system.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from pymongo import MongoClient
from config import MONGO_URI
from ml_service import MLService

def main():
    print("=" * 70)
    print("  MIGRATION: Populate Person Predictions")
    print("=" * 70)

    # Connect to database
    client = MongoClient(MONGO_URI)
    db = client.get_database()

    print(f"\nConnected to database: {db.name}")

    # Initialize ML Service
    print("\nInitializing ML Service...")
    try:
        ml_service = MLService(db)
        print("[OK] ML Service initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize ML Service: {e}")
        return

    # Get all persons
    persons = list(db.persons.find({}, {"person_id": 1, "name": 1}))
    total_persons = len(persons)

    if total_persons == 0:
        print("\n[WARN] No persons found in database")
        return

    print(f"\nFound {total_persons} persons to analyze")
    print("-" * 70)

    # Analyze each person
    analyzed = 0
    insufficient_data = 0
    errors = 0

    for i, person in enumerate(persons, 1):
        person_id = person["person_id"]
        name = person.get("name", "Unknown")

        print(f"\n[{i}/{total_persons}] Analyzing {person_id} ({name})...")

        try:
            result = ml_service.analyze_person(person_id)

            if result.get("status") == "insufficient_data":
                print(f"  [WARN] Insufficient data ({result.get('record_count', 0)} days)")
                insufficient_data += 1
            elif result.get("status") == "error":
                print(f"  [ERROR] Error: {result.get('error')}")
                errors += 1
            else:
                alert_level = result.get("alert_level", "UNKNOWN")
                risk_score = result.get("combined_risk_score", 0)
                print(f"  [OK] {alert_level} (risk: {risk_score:.0%})")
                analyzed += 1
        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            errors += 1

    print("\n" + "=" * 70)
    print("  MIGRATION COMPLETE")
    print("=" * 70)
    print(f"\nResults:")
    print(f"  Total persons: {total_persons}")
    print(f"  [OK] Analyzed successfully: {analyzed}")
    print(f"  [WARN] Insufficient data: {insufficient_data}")
    print(f"  [ERROR] Errors: {errors}")

    # Show summary by alert level
    if analyzed > 0:
        print(f"\nAlert Level Summary:")
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = db.person_predictions.count_documents({"alert_level": level})
            if count > 0:
                print(f"  {level}: {count}")

    print("\n[OK] person_predictions collection is now populated")
    print("[OK] Dashboard will now show real-time predictions")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
