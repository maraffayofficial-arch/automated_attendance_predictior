"""
==========================================================
 MODEL 3: ISOLATION FOREST — Anomaly Detection (v2)
 
 ANOMALY TYPES DETECTED:
   1. SUDDEN_DROP       — Was attending well, suddenly stopped
   2. EXAM_ABSENCE      — (handled in alert_system as rule-based)
   3. PERFECT_THEN_ABSENT — Consistently good, then complete absence
   4. ERRATIC_PATTERN   — Unpredictable on-off attendance
   
   + PROLONGED_ABSENCE  — Extended continuous absence streak
   
 NEW FEATURES USED:
   - attendance_variance_14d  → catches erratic patterns
   - short_long_avg_gap       → catches sudden drops
==========================================================
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import joblib
import json
import os
from datetime import datetime

# from feature_engineering import (
#     engineer_features,
#     get_anomaly_columns,
#     get_person_features,
# )


def prepare_anomaly_data(featured_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare per-person summary features for anomaly detection.
    Uses the LAST 14 DAYS of data per person.
    """
    anomaly_cols = get_anomaly_columns()
    
    df = featured_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    
    max_date = df["date"].max()
    cutoff = max_date - pd.Timedelta(days=20)
    recent = df[df["date"] > cutoff]
    
    summaries = []
    for person_id, group in recent.groupby("person_id"):
        summary = {
            "person_id": person_id,
            # Latest values
            "rolling_avg_7d": group["rolling_avg_7d"].iloc[-1],
            "rolling_avg_30d": group["rolling_avg_30d"].iloc[-1],
            "consecutive_absences": group["consecutive_absences"].iloc[-1],
            "z_score_deviation": group["z_score_deviation"].iloc[-1],
            "attendance_trend": group["attendance_trend"].iloc[-1],
            "attendance_variance_14d": group["attendance_variance_14d"].iloc[-1],
            "short_long_avg_gap": group["short_long_avg_gap"].iloc[-1],
            # Context for reporting
            "recent_attendance_rate": group["attendance_binary"].mean(),
            "recent_days_tracked": len(group),
        }
        summaries.append(summary)
    
    return pd.DataFrame(summaries)


def classify_anomaly_type(row: pd.Series) -> str:
    """
    Classify WHY a person is anomalous.
    
    Priority order matters — check most severe first.
    
    Types:
      PERFECT_THEN_ABSENT — Was consistently good (30d avg > 0.80)
                            but now has 3+ consecutive absences.
                            This is alarming because it breaks character.
      
      PROLONGED_ABSENCE   — 5+ consecutive absences regardless of history.
                            Needs immediate welfare check.
      
      SUDDEN_DROP         — 30-day avg is significantly higher than 7-day avg
                            (gap > 0.25). Recent behavior is much worse than
                            their established pattern.
      
      ERRATIC_PATTERN     — High attendance variance (> 0.20 over 14 days).
                            Person alternates present/absent unpredictably.
                            Average might look okay but pattern is unstable.
    """
    rolling_7d = row["rolling_avg_7d"]
    rolling_30d = row["rolling_avg_30d"]
    consec = row["consecutive_absences"]
    variance = row["attendance_variance_14d"]
    gap = row["short_long_avg_gap"]
    
    # 3. PERFECT_THEN_ABSENT: was good, now gone
    if rolling_30d >= 0.80 and consec >= 3:
        return "PERFECT_THEN_ABSENT"
    
    # PROLONGED_ABSENCE: extended streak
    if consec >= 5:
        return "PROLONGED_ABSENCE"
    
    # 1. SUDDEN_DROP: recent performance much worse than history
    if gap >= 0.25 and rolling_7d < 0.50:
        return "SUDDEN_DROP"
    
    # 6. ERRATIC_PATTERN: high variance, unpredictable
    if variance >= 0.20:
        return "ERRATIC_PATTERN"
    
    # If flagged by Isolation Forest but doesn't match specific types
    # Still an anomaly, just less clearly categorized
    if consec >= 3:
        return "PROLONGED_ABSENCE"
    if gap >= 0.15:
        return "SUDDEN_DROP"
    if variance >= 0.15:
        return "ERRATIC_PATTERN"
    
    return "IRREGULAR_PATTERN"


def train_isolation_forest(
    summary_df: pd.DataFrame,
    contamination: float = 0.15,
    save_path: str = "models/isolation_forest_model.pkl"
) -> tuple:
    """Train Isolation Forest on per-person behavioral summaries."""
    print("=" * 60)
    print("  TRAINING ISOLATION FOREST (v2)")
    print("=" * 60)
    
    anomaly_cols = get_anomaly_columns()
    X = summary_df[anomaly_cols].copy()
    
    print(f"Persons analyzed: {len(X)}")
    print(f"Features ({len(anomaly_cols)}): {anomaly_cols}")
    print(f"Contamination rate: {contamination:.0%}")
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        max_samples="auto",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)
    
    # Get results
    raw_scores = model.decision_function(X_scaled)
    predictions = model.predict(X_scaled)
    
    # Normalize anomaly scores to [0, 1]
    anomaly_scores = -raw_scores
    min_s, max_s = anomaly_scores.min(), anomaly_scores.max()
    if max_s > min_s:
        anomaly_scores = (anomaly_scores - min_s) / (max_s - min_s)
    else:
        anomaly_scores = np.zeros_like(anomaly_scores)
    
    # Build results
    results = summary_df.copy()
    results["anomaly_score"] = np.round(anomaly_scores, 4)
    results["is_anomaly"] = (predictions == -1)
    results["raw_isolation_score"] = np.round(raw_scores, 4)
    
    # Classify anomaly types
    results["anomaly_type"] = "NORMAL"
    for idx, row in results.iterrows():
        if row["is_anomaly"]:
            results.loc[idx, "anomaly_type"] = classify_anomaly_type(row)
    
    results = results.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
    
    # Save
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    joblib.dump({"model": model, "scaler": scaler}, save_path)
    print(f"Model saved to: {save_path}")
    
    # Summary
    n_anomalies = results["is_anomaly"].sum()
    print(f"\nResults:")
    print(f"  Total persons:  {len(results)}")
    print(f"  Anomalies:      {n_anomalies} ({n_anomalies/len(results):.0%})")
    print(f"  Normal:         {len(results) - n_anomalies}")
    
    if n_anomalies > 0:
        print(f"\nAnomaly Type Breakdown:")
        type_counts = results[results["is_anomaly"]]["anomaly_type"].value_counts()
        for atype, count in type_counts.items():
            print(f"    {atype}: {count}")
    
    return model, scaler, results


def detect_anomaly_single(model, scaler, featured_df, person_id) -> dict:
    """Check if a specific person's recent behavior is anomalous."""
    anomaly_cols = get_anomaly_columns()
    person_data = get_person_features(featured_df, person_id)
    
    latest = person_data.iloc[-1:]
    X = latest[anomaly_cols]
    
    X_scaled = scaler.transform(X)
    raw_score = float(model.decision_function(X_scaled)[0])
    prediction = model.predict(X_scaled)[0]
    is_anomaly = prediction == -1
    
    anomaly_type = "NORMAL"
    if is_anomaly:
        anomaly_type = classify_anomaly_type(latest.iloc[0])
    
    return {
        "person_id": person_id,
        "is_anomaly": bool(is_anomaly),
        "anomaly_type": anomaly_type,
        "isolation_score": round(raw_score, 4),
        "current_features": {
            col: round(float(latest[col].values[0]), 4)
            for col in anomaly_cols
        }
    }


def plot_anomaly_results(results: pd.DataFrame):
    """Plot anomaly detection results."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Anomaly scores
    ax1 = axes[0]
    colors = ["#f44336" if a else "#4caf50" for a in results["is_anomaly"]]
    ax1.bar(range(len(results)), results["anomaly_score"], color=colors, width=0.8)
    
    if results["is_anomaly"].any():
        anomaly_min = results[results["is_anomaly"]]["anomaly_score"].min()
        ax1.axhline(y=anomaly_min, color="#f44336", linestyle="--", alpha=0.7, label="Threshold")
    
    ax1.set_xlabel("Persons (sorted by anomaly score)")
    ax1.set_ylabel("Anomaly Score")
    ax1.set_title("Isolation Forest: Anomaly Scores", fontsize=13, fontweight="bold")
    ax1.legend()
    ax1.grid(True, axis="y", alpha=0.3)
    
    # Plot 2: Scatter — short_long_avg_gap vs variance
    ax2 = axes[1]
    normal = results[~results["is_anomaly"]]
    anomalies = results[results["is_anomaly"]]
    
    ax2.scatter(normal["short_long_avg_gap"], normal["attendance_variance_14d"],
               c="#4caf50", alpha=0.6, s=80, label="Normal", edgecolors="white")
    
    type_colors = {
        "SUDDEN_DROP": "#ff5722",
        "PERFECT_THEN_ABSENT": "#d32f2f",
        "ERRATIC_PATTERN": "#9c27b0",
        "PROLONGED_ABSENCE": "#f44336",
        "IRREGULAR_PATTERN": "#ff9800",
    }
    
    for _, row in anomalies.iterrows():
        color = type_colors.get(row["anomaly_type"], "#f44336")
        ax2.scatter(row["short_long_avg_gap"], row["attendance_variance_14d"],
                   c=color, s=120, marker="X", edgecolors="white", linewidths=1.5,
                   zorder=5)
        ax2.annotate(f"{row['person_id']}\n({row['anomaly_type']})",
                    (row["short_long_avg_gap"], row["attendance_variance_14d"]),
                    fontsize=6, ha="center", va="bottom", color=color, fontweight="bold")
    
    ax2.set_xlabel("Short-Long Avg Gap (30d - 7d)")
    ax2.set_ylabel("Attendance Variance (14d)")
    ax2.set_title("Anomaly Map: Sudden Drops vs Erratic Patterns",
                 fontsize=13, fontweight="bold")
    ax2.axhline(y=0.20, color="#9c27b0", linestyle=":", alpha=0.5, label="Erratic threshold")
    ax2.axvline(x=0.25, color="#ff5722", linestyle=":", alpha=0.5, label="Sudden drop threshold")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("isolation_forest_results.png", dpi=150, bbox_inches="tight")
    print("Plot saved: isolation_forest_results.png")
    plt.close()


def plot_anomaly_types(results: pd.DataFrame):
    """Plot breakdown of anomaly types."""
    anomalies = results[results["is_anomaly"]]
    if anomalies.empty:
        print("No anomalies detected — skipping type plot.")
        return
    
    type_counts = anomalies["anomaly_type"].value_counts()
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    type_colors = {
        "PERFECT_THEN_ABSENT": "#d32f2f",
        "PROLONGED_ABSENCE": "#f44336",
        "SUDDEN_DROP": "#ff5722",
        "ERRATIC_PATTERN": "#9c27b0",
        "IRREGULAR_PATTERN": "#ff9800",
    }
    colors = [type_colors.get(t, "#757575") for t in type_counts.index]
    
    bars = ax.barh(type_counts.index, type_counts.values, color=colors)
    for bar, count in zip(bars, type_counts.values):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
               f"{count} persons", va="center", fontweight="bold")
    
    ax.set_xlabel("Count")
    ax.set_title("Anomaly Type Breakdown", fontsize=13, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("isolation_forest_anomaly_types.png", dpi=150, bbox_inches="tight")
    print("Plot saved: isolation_forest_anomaly_types.png")
    plt.close()


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
if __name__ == "__main__":
    
    try:
        featured_df = pd.read_csv("featured_attendance_data.csv")
        featured_df["date"] = pd.to_datetime(featured_df["date"])
    except FileNotFoundError:
        print("ERROR: featured_attendance_data.csv not found.")
        print("Run generate_synthetic_data.py and feature_engineering.py first.")
        exit(1)
    
    print("Preparing per-person behavioral summaries...\n")
    summary_df = prepare_anomaly_data(featured_df)
    
    model, scaler, results = train_isolation_forest(summary_df, contamination=0.15)
    
    # Flagged persons
    print("\n" + "=" * 60)
    print("  FLAGGED PERSONS")
    print("=" * 60)
    
    anomalies = results[results["is_anomaly"]]
    display_cols = [
        "person_id", "anomaly_score", "anomaly_type",
        "rolling_avg_7d", "rolling_avg_30d", "consecutive_absences",
        "attendance_variance_14d", "short_long_avg_gap",
        "recent_attendance_rate"
    ]
    
    if not anomalies.empty:
        print(anomalies[display_cols].to_string(index=False))
    
    # Most normal
    print("\n--- Most Normal Persons ---")
    normal = results[~results["is_anomaly"]].tail(5)
    print(normal[display_cols].to_string(index=False))
    
    # Plots
    print()
    plot_anomaly_results(results)
    plot_anomaly_types(results)
    
    # Demo
    print("\n" + "=" * 60)
    print("  DEMO: CHECK SPECIFIC PERSONS")
    print("=" * 60)
    
    demo_persons = [results.iloc[0]["person_id"], results.iloc[-1]["person_id"]]
    for pid in demo_persons:
        result = detect_anomaly_single(model, scaler, featured_df, pid)
        status = "ANOMALY" if result["is_anomaly"] else "NORMAL"
        print(f"\n  {pid}: {status}")
        print(f"    Type: {result['anomaly_type']}")
        print(f"    Features: {result['current_features']}")
    
    # Save report
    report = {
        "model": "Isolation Forest v2",
        "generated_at": datetime.now().isoformat(),
        "anomaly_types_supported": [
            "SUDDEN_DROP", "PERFECT_THEN_ABSENT",
            "ERRATIC_PATTERN", "PROLONGED_ABSENCE"
        ],
        "total_persons": len(results),
        "anomalies_detected": int(results["is_anomaly"].sum()),
        "anomaly_breakdown": results[results["is_anomaly"]][
            ["person_id", "anomaly_score", "anomaly_type"]
        ].to_dict("records"),
    }
    
    with open("isolation_forest_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: isolation_forest_report.json")
    
    print("\n" + "=" * 60)
    print("  ISOLATION FOREST v2 COMPLETE")
    print("=" * 60)