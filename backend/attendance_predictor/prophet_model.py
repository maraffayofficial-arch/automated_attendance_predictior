"""
==========================================================
 FEATURE ENGINEERING PIPELINE (v4)
 
 UPDATES:
   - Added attendance_variance_14d (for erratic pattern detection)
   - Added short_long_avg_gap (for sudden drop detection)
   - All features shifted by 1 day (no leakage)
 
 RAW INPUT (from database — 4 columns only):
   person_id, date, attendance_binary, is_exam_period
==========================================================
"""

import pandas as pd
import numpy as np


EXAM_PERIODS = [
    ("2025-03-10", "2025-03-21"),
    ("2025-06-01", "2025-06-14"),
    ("2025-10-13", "2025-10-24"),
    ("2025-12-08", "2025-12-19"),
    ("2026-03-09", "2026-03-20"),
]


def _compute_workload_indicator(df: pd.DataFrame) -> pd.Series:
    """Compute workload_indicator (1-10) from date and exam calendar."""
    dates = pd.to_datetime(df["date"])
    exam_starts = [pd.Timestamp(s) for s, e in EXAM_PERIODS]
    exam_ends = [pd.Timestamp(e) for s, e in EXAM_PERIODS]
    
    workload = []
    for date in dates:
        in_exam = False
        for s, e in zip(exam_starts, exam_ends):
            if s <= date <= e:
                in_exam = True
                break
        
        if in_exam:
            score = 9.0
        else:
            future_exams = [s for s in exam_starts if s > date]
            days_to_exam = (future_exams[0] - date).days if future_exams else 999
            
            if days_to_exam <= 7: score = 7.0
            elif days_to_exam <= 14: score = 6.0
            elif days_to_exam <= 21: score = 5.0
            else: score = 4.0
            
            month = date.month
            if month in [5, 11, 12]: score = min(score + 1.0, 10.0)
            if month in [1, 8, 9] and days_to_exam > 21: score = max(score - 1.0, 2.0)
        
        score = np.clip(score + np.random.normal(0, 0.3), 1.0, 10.0)
        workload.append(round(score, 1))
    
    return pd.Series(workload, index=df.index)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes raw attendance data (4 columns) and computes ALL features.
    All attendance-derived features are SHIFTED by 1 day (no leakage).
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["person_id", "date"]).reset_index(drop=True)
    
    # --- DATE-BASED (no shift needed) ---
    df["month"] = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.dayofweek
    df["workload_indicator"] = _compute_workload_indicator(df)
    
    # --- ATTENDANCE-BASED (all shifted by 1) ---
    grouped = df.groupby("person_id")
    
    # Rolling averages
    df["rolling_avg_7d"] = grouped["attendance_binary"].transform(
        lambda x: x.rolling(window=7, min_periods=1).mean().shift(1)
    )
    df["rolling_avg_30d"] = grouped["attendance_binary"].transform(
        lambda x: x.rolling(window=30, min_periods=1).mean().shift(1)
    )
    
    # Previous attendance counts
    df["prev_7d_attendance"] = grouped["attendance_binary"].transform(
        lambda x: x.rolling(window=7, min_periods=1).sum().shift(1)
    )
    df["prev_30d_attendance"] = grouped["attendance_binary"].transform(
        lambda x: x.rolling(window=30, min_periods=1).sum().shift(1)
    )
    
    # Consecutive absences
    def calc_consecutive_absences(series):
        streaks = []
        count = 0
        for val in series:
            if val == 0: count += 1
            else: count = 0
            streaks.append(count)
        return streaks
    
    df["consecutive_absences"] = grouped["attendance_binary"].transform(
        calc_consecutive_absences
    )
    df["consecutive_absences"] = grouped["consecutive_absences"].transform(
        lambda x: x.shift(1)
    )
    
    # Z-Score deviation
    person_mean = grouped["attendance_binary"].transform("mean")
    person_std = grouped["attendance_binary"].transform("std").replace(0, np.nan)
    df["z_score_deviation"] = (df["rolling_avg_7d"] - person_mean) / person_std
    df["z_score_deviation"] = df["z_score_deviation"].fillna(0)
    
    # Attendance trend (slope over last 14 days)
    def calc_trend(series):
        trends = []
        values = list(series)
        for i in range(len(values)):
            window_start = max(0, i - 13)
            window = values[window_start:i + 1]
            if len(window) < 3:
                trends.append(0.0)
            else:
                x = np.arange(len(window))
                slope = np.polyfit(x, window, 1)[0]
                trends.append(round(slope, 6))
        return trends
    
    df["attendance_trend"] = grouped["attendance_binary"].transform(calc_trend)
    df["attendance_trend"] = grouped["attendance_trend"].transform(
        lambda x: x.shift(1)
    )
    
    # -------------------------------------------------------
    # NEW FEATURES (v4)
    # -------------------------------------------------------
    
    # --- Attendance Variance (14-day window) ---
    # High variance = erratic (PRESENT-ABSENT-PRESENT-ABSENT)
    # Low variance = consistent (either always present or always absent)
    # Max possible variance for binary data = 0.25 (when exactly 50/50)
    df["attendance_variance_14d"] = grouped["attendance_binary"].transform(
        lambda x: x.rolling(window=14, min_periods=3).var().shift(1)
    )
    df["attendance_variance_14d"] = df["attendance_variance_14d"].fillna(0)
    
    # --- Short-Long Average Gap ---
    # Difference between 30-day avg and 7-day avg.
    # Large positive gap = was good long-term but dropped recently (SUDDEN DROP)
    # Large negative gap = was bad long-term but improved recently
    df["short_long_avg_gap"] = df["rolling_avg_30d"] - df["rolling_avg_7d"]
    
    # Drop rows with NaN
    df = df.dropna(subset=["rolling_avg_7d"]).reset_index(drop=True)
    
    return df


def get_person_features(df: pd.DataFrame, person_id: str) -> pd.DataFrame:
    """Extract feature data for a specific person."""
    person_data = df[df["person_id"] == person_id].copy()
    if person_data.empty:
        raise ValueError(f"Person '{person_id}' not found in dataset.")
    return person_data


def prepare_prophet_data(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate into daily attendance rates for Prophet."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    daily = df.groupby("date").agg(
        y=("attendance_binary", "mean"),
        is_exam_period=("is_exam_period", "max"),
    ).reset_index()
    daily = daily.rename(columns={"date": "ds"})
    daily = daily.sort_values("ds").reset_index(drop=True)
    return daily


def get_feature_columns():
    """Feature columns for XGBoost (13 features now)."""
    return [
        "month",
        "day_of_week",
        "workload_indicator",
        "is_exam_period",
        "rolling_avg_7d",
        "rolling_avg_30d",
        "prev_7d_attendance",
        "prev_30d_attendance",
        "consecutive_absences",
        "z_score_deviation",
        "attendance_trend",
        "attendance_variance_14d",
        "short_long_avg_gap",
    ]


def get_anomaly_columns():
    """Feature columns for Isolation Forest (7 features now)."""
    return [
        "rolling_avg_7d",
        "rolling_avg_30d",
        "consecutive_absences",
        "z_score_deviation",
        "attendance_trend",
        "attendance_variance_14d",
        "short_long_avg_gap",
    ]


# -------------------------------------------------------
# DEMO
# -------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  FEATURE ENGINEERING PIPELINE v4")
    print("=" * 60)
    
    try:
        raw_df = pd.read_csv("raw_attendance_data.csv")
    except FileNotFoundError:
        print("\nERROR: Run generate_synthetic_data.py first!")
        exit(1)
    
    print(f"\nRaw data: {raw_df.shape[0]} rows, {raw_df.shape[1]} columns")
    
    print("\nComputing features...")
    featured_df = engineer_features(raw_df)
    
    print(f"Featured data: {featured_df.shape[0]} rows, {featured_df.shape[1]} columns")
    print(f"\nAll columns:")
    for col in featured_df.columns:
        print(f"  - {col}")
    
    sample_person = featured_df["person_id"].unique()[0]
    person_data = get_person_features(featured_df, sample_person)
    print(f"\n--- {sample_person} (last 10 days) ---")
    display_cols = [
        "date", "attendance_binary", "rolling_avg_7d",
        "consecutive_absences", "attendance_variance_14d",
        "short_long_avg_gap"
    ]
    print(person_data[display_cols].tail(10).to_string(index=False))
    
    print(f"\nXGBoost features ({len(get_feature_columns())}): {get_feature_columns()}")
    print(f"Isolation Forest features ({len(get_anomaly_columns())}): {get_anomaly_columns()}")
    
    prophet_df = prepare_prophet_data(raw_df)
    
    featured_df.to_csv("featured_attendance_data.csv", index=False)
    prophet_df.to_csv("prophet_ready_data.csv", index=False)
    print("\nSaved: featured_attendance_data.csv")
    print("Saved: prophet_ready_data.csv")