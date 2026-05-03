"""
==========================================================
 SYNTHETIC DATA GENERATOR (v2)
 
 Generates realistic raw attendance data matching your DB schema.
 
 RAW FEATURES (what your teammates provide from the database):
   - person_id
   - date
   - attendance_binary
   - is_exam_period
     
 That's it. Everything else is computed by feature_engineering.py.
 
 Run this ONCE to create sample data for development/testing.
 In production, this file is NOT needed — real data comes from the DB.
==========================================================
"""

import pandas as pd
import numpy as np

# --- Define exam periods (realistic academic calendar) ---
EXAM_PERIODS = [
    ("2025-03-10", "2025-03-21"),  # Mid-term 1
    ("2025-06-01", "2025-06-14"),  # Final 1
    ("2025-10-13", "2025-10-24"),  # Mid-term 2
    ("2025-12-08", "2025-12-19"),  # Final 2
    ("2026-03-09", "2026-03-20"),  # Mid-term 3
]


def is_exam(date):
    for start, end in EXAM_PERIODS:
        if pd.Timestamp(start) <= date <= pd.Timestamp(end):
            return 1
    return 0


def generate_synthetic_data(
    n_persons: int = 50,
    start_date: str = "2025-01-01",
    end_date: str = "2026-03-31",
    seed: int = 42
) -> pd.DataFrame:
    """
    Generate realistic attendance data with ONLY the 4 raw columns
    that a real database would provide.
    """
    np.random.seed(seed)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
    
    # --- Assign profiles to persons ---
    profiles = []
    for pid in range(1, n_persons + 1):
        r = np.random.random()
        if r < 0.35:
            profiles.append(("regular", pid))
        elif r < 0.65:
            profiles.append(("average", pid))
        elif r < 0.85:
            profiles.append(("at_risk", pid))
        else:
            profiles.append(("erratic", pid))
    
    records = []
    
    for profile_type, pid in profiles:
        person_id = f"EMP-{pid:04d}"
        
        if profile_type == "regular":
            base_prob = 0.92
        elif profile_type == "average":
            base_prob = 0.75
        elif profile_type == "at_risk":
            base_prob = 0.55
        else:
            base_prob = 0.85
        
        consecutive_absent = 0
        
        for i, date in enumerate(dates):
            exam = is_exam(date)
            month = date.month
            
            # Hidden factors (drive realistic patterns but are NOT features)
            internal_stress = np.clip(np.random.normal(7.5 if exam else 4, 1.5), 1, 10)
            internal_workload = np.clip(np.random.normal(8 if exam else 5, 2), 1, 10)
            
            prob = base_prob
            
            if internal_stress > 7:
                prob -= 0.1
            if internal_workload > 7:
                prob -= 0.05
            if exam:
                if profile_type in ["at_risk", "erratic"]:
                    prob -= 0.15
                else:
                    prob += 0.05
            if consecutive_absent >= 2:
                prob -= 0.1 * min(consecutive_absent, 5)
            if profile_type == "erratic":
                day_index = (date - dates[0]).days
                if 120 < day_index < 145 or 250 < day_index < 270:
                    prob = 0.3
            if month in [12, 1, 2]:
                prob -= 0.05
            
            prob = np.clip(prob, 0.05, 0.98)
            attendance = 1 if np.random.random() < prob else 0
            
            if attendance == 0:
                consecutive_absent += 1
            else:
                consecutive_absent = 0
            
            records.append({
                "person_id": person_id,
                "date": date,
                "attendance_binary": attendance,
                "is_exam_period": exam,
            })
    
    df = pd.DataFrame(records)
    df = df.sort_values(["person_id", "date"]).reset_index(drop=True)
    return df


if __name__ == "__main__":
    print("Generating synthetic attendance data...")
    df = generate_synthetic_data(n_persons=50)
    df.to_csv("raw_attendance_data.csv", index=False)
    
    print(f"Generated {len(df)} records for {df['person_id'].nunique()} persons")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Overall attendance rate: {df['attendance_binary'].mean():.2%}")
    print(f"\nRaw columns (only these come from the database):")
    print(f"  {list(df.columns)}")
    print(f"\nSample rows:")
    print(df.head(10).to_string(index=False))
    print(f"\nSaved to: raw_attendance_data.csv")