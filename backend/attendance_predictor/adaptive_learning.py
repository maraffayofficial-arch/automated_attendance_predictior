"""
==========================================================
 ALERT SYSTEM (v2) — Combines All 3 Models
 
 ANOMALY TYPES IN FINAL OUTPUT:
   From Isolation Forest:
     1. SUDDEN_DROP        — Recent attendance much worse than history
     3. PERFECT_THEN_ABSENT — Was consistent, now completely gone
     6. ERRATIC_PATTERN    — Unpredictable on-off attendance
     +  PROLONGED_ABSENCE  — Extended absence streak
   
   From Rule-Based Check (this script):
     2. EXAM_ABSENCE       — Absent during exam periods
==========================================================
"""

import pandas as pd
import numpy as np
import joblib
import json
import os
from datetime import datetime

from prophet_model import (
    engineer_features,
    get_feature_columns,
    get_anomaly_columns,
    get_person_features,
    prepare_prophet_data,
    EXAM_PERIODS,
)


# -------------------------------------------------------
# THRESHOLDS
# -------------------------------------------------------
THRESHOLDS = {
    "xgboost_high": 0.60,
    "xgboost_medium": 0.35,
    "anomaly_boost": 0.15,
    "prophet_declining_boost": 0.05,
    "predicted_absences_high": 4,
    "exam_absence_rate_threshold": 0.30,  # if absent > 30% during exams → flag
}


def load_models(models_dir="models"):
    """Load all 3 trained models."""
    models = {}
    
    prophet_path = os.path.join(models_dir, "prophet_model.pkl")
    if os.path.exists(prophet_path):
        models["prophet"] = joblib.load(prophet_path)
        print("  Prophet loaded")
    else:
        print("  WARNING: Prophet not found — skipping group trend")
        models["prophet"] = None
    
    xgboost_path = os.path.join(models_dir, "xgboost_model.pkl")
    if os.path.exists(xgboost_path):
        models["xgboost"] = joblib.load(xgboost_path)
        print("  XGBoost loaded")
    else:
        raise FileNotFoundError("XGBoost model not found.")
    
    iso_path = os.path.join(models_dir, "isolation_forest_model.pkl")
    if os.path.exists(iso_path):
        iso_data = joblib.load(iso_path)
        models["isolation_forest"] = iso_data["model"]
        models["iso_scaler"] = iso_data["scaler"]
        print("  Isolation Forest loaded")
    else:
        raise FileNotFoundError("Isolation Forest model not found.")
    
    return models


def get_prophet_trend(models, prophet_df):
    """Get Prophet's group-level trend."""
    if models["prophet"] is None:
        return {"trend": "UNKNOWN", "current_rate": None, "forecast_rate": None}
    
    model = models["prophet"]
    last_date = prophet_df["ds"].max()
    future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=7)
    future = pd.DataFrame({"ds": future_dates})
    future["is_exam_period"] = 0
    
    forecast = model.predict(future)
    forecast["yhat"] = forecast["yhat"].clip(0, 1)
    
    current_rate = prophet_df["y"].tail(7).mean()
    forecast_rate = forecast["yhat"].mean()
    
    if forecast_rate < current_rate - 0.03: trend = "DECLINING"
    elif forecast_rate > current_rate + 0.03: trend = "IMPROVING"
    else: trend = "STABLE"
    
    return {
        "trend": trend,
        "current_rate": round(float(current_rate), 4),
        "forecast_rate": round(float(forecast_rate), 4),
    }


def check_exam_absence(featured_df, person_id):
    """
    RULE-BASED CHECK: Exam Absence Detection.
    
    Not an ML model — just a direct check:
    "Was this person absent during exam periods?"
    
    Returns exam absence info if concerning.
    """
    person_data = get_person_features(featured_df, person_id)
    
    exam_days = person_data[person_data["is_exam_period"] == 1]
    
    if exam_days.empty:
        return {"has_exam_absence": False, "exam_absence_rate": 0, "exam_days_missed": 0}
    
    # Check last exam period only (most recent)
    last_exam_end = exam_days["date"].max()
    last_exam_start = last_exam_end - pd.Timedelta(days=15)
    recent_exam = exam_days[exam_days["date"] >= last_exam_start]
    
    if recent_exam.empty:
        return {"has_exam_absence": False, "exam_absence_rate": 0, "exam_days_missed": 0}
    
    exam_absence_rate = 1 - recent_exam["attendance_binary"].mean()
    exam_days_missed = int((recent_exam["attendance_binary"] == 0).sum())
    total_exam_days = len(recent_exam)
    
    is_concerning = exam_absence_rate >= THRESHOLDS["exam_absence_rate_threshold"]
    
    return {
        "has_exam_absence": is_concerning,
        "exam_absence_rate": round(float(exam_absence_rate), 4),
        "exam_days_missed": exam_days_missed,
        "total_exam_days": total_exam_days,
    }


def get_xgboost_risk(models, featured_df, person_id):
    """Get XGBoost's individual risk with 7-day forecast."""
    feature_cols = get_feature_columns()
    model = models["xgboost"]
    
    person_data = get_person_features(featured_df, person_id)
    latest = person_data.iloc[-1:]
    X = latest[feature_cols]
    absence_prob = float(model.predict_proba(X)[0][1])
    
    # 7-day recursive forecast
    recent_attendance = list(person_data["attendance_binary"].tail(30).values)
    last_date = pd.to_datetime(person_data["date"].iloc[-1])
    person_mean = person_data["attendance_binary"].mean()
    person_std = max(person_data["attendance_binary"].std(), 0.001)
    
    forecast_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=7)
    daily_forecasts = []
    
    for forecast_date in forecast_dates:
        month = forecast_date.month
        day_of_week = forecast_date.dayofweek
        
        is_exam = 0
        for s, e in EXAM_PERIODS:
            if pd.Timestamp(s) <= forecast_date <= pd.Timestamp(e):
                is_exam = 1
                break
        
        exam_starts = [pd.Timestamp(s) for s, e in EXAM_PERIODS]
        if is_exam:
            workload = 9.0
        else:
            future_exams = [s for s in exam_starts if s > forecast_date]
            days_to_exam = (future_exams[0] - forecast_date).days if future_exams else 999
            if days_to_exam <= 7: workload = 7.0
            elif days_to_exam <= 14: workload = 6.0
            elif days_to_exam <= 21: workload = 5.0
            else: workload = 4.0
            if month in [5, 11, 12]: workload = min(workload + 1.0, 10.0)
            if month in [1, 8, 9] and days_to_exam > 21: workload = max(workload - 1.0, 2.0)
        
        last_7 = recent_attendance[-7:]
        last_30 = recent_attendance[-30:]
        last_14 = recent_attendance[-14:]
        
        consec = 0
        for val in reversed(recent_attendance):
            if val == 0: consec += 1
            else: break
        
        trend = np.polyfit(np.arange(len(last_14)), last_14, 1)[0] if len(last_14) >= 3 else 0.0
        
        r7 = np.mean(last_7)
        r30 = np.mean(last_30)
        
        # Compute variance for last 14 values
        variance_14d = np.var(last_14) if len(last_14) >= 3 else 0.0
        
        fv = pd.DataFrame([{
            "month": month, "day_of_week": day_of_week,
            "workload_indicator": workload, "is_exam_period": is_exam,
            "rolling_avg_7d": r7, "rolling_avg_30d": r30,
            "prev_7d_attendance": sum(last_7), "prev_30d_attendance": sum(last_30),
            "consecutive_absences": consec,
            "z_score_deviation": (r7 - person_mean) / person_std,
            "attendance_trend": trend,
            "attendance_variance_14d": variance_14d,
            "short_long_avg_gap": r30 - r7,
        }])[feature_cols]
        
        prob = float(model.predict_proba(fv)[0][1])
        predicted_attendance = 0 if prob >= 0.5 else 1
        
        daily_forecasts.append({
            "date": forecast_date.strftime("%Y-%m-%d"),
            "absence_probability": round(prob, 4),
            "predicted_status": "ABSENT" if prob >= 0.5 else "PRESENT",
        })
        
        recent_attendance.append(predicted_attendance)
    
    predicted_absences = sum(1 for d in daily_forecasts if d["predicted_status"] == "ABSENT")
    
    return {
        "current_absence_probability": round(absence_prob, 4),
        "predicted_absences_7d": predicted_absences,
        "avg_risk_7d": round(np.mean([d["absence_probability"] for d in daily_forecasts]), 4),
        "daily_forecasts": daily_forecasts,
    }


def get_anomaly_status(models, featured_df, person_id):
    """Get Isolation Forest's anomaly assessment."""
    anomaly_cols = get_anomaly_columns()
    model = models["isolation_forest"]
    scaler = models["iso_scaler"]
    
    person_data = get_person_features(featured_df, person_id)
    latest = person_data.iloc[-1:]
    X = latest[anomaly_cols]
    
    X_scaled = scaler.transform(X)
    raw_score = float(model.decision_function(X_scaled)[0])
    prediction = model.predict(X_scaled)[0]
    is_anomaly = prediction == -1
    
    anomaly_type = "NORMAL"
    if is_anomaly:
        row = latest.iloc[0]
        # Use same classification logic
        r7 = row["rolling_avg_7d"]
        r30 = row["rolling_avg_30d"]
        consec = row["consecutive_absences"]
        variance = row["attendance_variance_14d"]
        gap = row["short_long_avg_gap"]
        
        if r30 >= 0.80 and consec >= 3:
            anomaly_type = "PERFECT_THEN_ABSENT"
        elif consec >= 5:
            anomaly_type = "PROLONGED_ABSENCE"
        elif gap >= 0.25 and r7 < 0.50:
            anomaly_type = "SUDDEN_DROP"
        elif variance >= 0.20:
            anomaly_type = "ERRATIC_PATTERN"
        elif consec >= 3:
            anomaly_type = "PROLONGED_ABSENCE"
        elif gap >= 0.15:
            anomaly_type = "SUDDEN_DROP"
        elif variance >= 0.15:
            anomaly_type = "ERRATIC_PATTERN"
        else:
            anomaly_type = "IRREGULAR_PATTERN"
    
    return {
        "is_anomaly": bool(is_anomaly),
        "anomaly_type": anomaly_type,
        "isolation_score": round(raw_score, 4),
    }


# -------------------------------------------------------
# ALERT DESCRIPTIONS (human-readable)
# -------------------------------------------------------
ANOMALY_DESCRIPTIONS = {
    "SUDDEN_DROP": "Attendance dropped sharply compared to recent history",
    "PERFECT_THEN_ABSENT": "Was consistently attending, then stopped completely",
    "ERRATIC_PATTERN": "Attendance is unpredictable — alternating present and absent",
    "PROLONGED_ABSENCE": "Extended continuous absence streak",
    "EXAM_ABSENCE": "Significant absences during exam period",
    "IRREGULAR_PATTERN": "Unusual attendance behavior detected",
}

ANOMALY_ACTIONS = {
    "SUDDEN_DROP": "Schedule meeting to identify cause of recent decline",
    "PERFECT_THEN_ABSENT": "Immediate welfare check — sudden disappearance from a reliable person",
    "ERRATIC_PATTERN": "Monitor pattern and discuss attendance consistency",
    "PROLONGED_ABSENCE": "Immediate outreach — person may need support",
    "EXAM_ABSENCE": "Academic counseling — missing exams may indicate serious issues",
    "IRREGULAR_PATTERN": "Add to watch list for closer monitoring",
}


def generate_person_alert(person_id, prophet_trend, xgboost_risk, anomaly_status, exam_check):
    """Combine all model outputs into a single alert."""
    reasons = []
    anomaly_types = []
    recommended_actions = []
    
    # --- Base risk from XGBoost ---
    base_risk = xgboost_risk["current_absence_probability"]
    combined_risk = base_risk
    
    # --- Isolation Forest anomaly ---
    if anomaly_status["is_anomaly"]:
        atype = anomaly_status["anomaly_type"]
        combined_risk += THRESHOLDS["anomaly_boost"]
        anomaly_types.append(atype)
        reasons.append(ANOMALY_DESCRIPTIONS.get(atype, "Anomalous behavior detected"))
        recommended_actions.append(ANOMALY_ACTIONS.get(atype, "Monitor closely"))
    
    # --- Exam absence (rule-based) ---
    if exam_check["has_exam_absence"]:
        anomaly_types.append("EXAM_ABSENCE")
        combined_risk += 0.10
        reasons.append(
            f"Missed {exam_check['exam_days_missed']}/{exam_check['total_exam_days']} "
            f"exam days ({exam_check['exam_absence_rate']:.0%} absence rate during exams)"
        )
        recommended_actions.append(ANOMALY_ACTIONS["EXAM_ABSENCE"])
    
    # --- Prophet trend ---
    if prophet_trend["trend"] == "DECLINING":
        combined_risk += THRESHOLDS["prophet_declining_boost"]
        reasons.append("Group attendance trend is declining")
    
    # --- XGBoost reasons ---
    if xgboost_risk["predicted_absences_7d"] >= THRESHOLDS["predicted_absences_high"]:
        reasons.append(f"Predicted absent {xgboost_risk['predicted_absences_7d']}/7 days next week")
        recommended_actions.append("Proactive outreach before absences accumulate")
    
    if base_risk >= THRESHOLDS["xgboost_high"]:
        reasons.append(f"High absence probability: {base_risk:.0%}")
    elif base_risk >= THRESHOLDS["xgboost_medium"]:
        reasons.append(f"Moderate absence probability: {base_risk:.0%}")
    
    # --- Alert level ---
    combined_risk = min(combined_risk, 1.0)
    
    if (combined_risk >= 0.8 or
        "PERFECT_THEN_ABSENT" in anomaly_types or
        "PROLONGED_ABSENCE" in anomaly_types or
        xgboost_risk["predicted_absences_7d"] >= 6):
        alert_level = "CRITICAL"
        if not recommended_actions:
            recommended_actions.append("Immediate intervention required")
    elif (combined_risk >= THRESHOLDS["xgboost_high"] or
          xgboost_risk["predicted_absences_7d"] >= 4 or
          "EXAM_ABSENCE" in anomaly_types):
        alert_level = "HIGH"
        if not recommended_actions:
            recommended_actions.append("Schedule meeting this week")
    elif combined_risk >= THRESHOLDS["xgboost_medium"] or "ERRATIC_PATTERN" in anomaly_types:
        alert_level = "MEDIUM"
        if not recommended_actions:
            recommended_actions.append("Add to watch list")
    else:
        alert_level = "LOW"
        reasons = ["Attendance pattern is healthy"]
        recommended_actions = ["No action needed"]
        anomaly_types = []
    
    return {
        "person_id": person_id,
        "alert_level": alert_level,
        "combined_risk_score": round(float(combined_risk), 4),
        "anomaly_types": anomaly_types,
        "reasons": reasons,
        "recommended_actions": recommended_actions,
        "model_details": {
            "xgboost": {
                "absence_probability": xgboost_risk["current_absence_probability"],
                "predicted_absences_7d": xgboost_risk["predicted_absences_7d"],
                "avg_risk_7d": xgboost_risk["avg_risk_7d"],
            },
            "isolation_forest": {
                "is_anomaly": anomaly_status["is_anomaly"],
                "anomaly_type": anomaly_status["anomaly_type"],
            },
            "prophet": {"group_trend": prophet_trend["trend"]},
            "exam_check": exam_check,
        },
        "daily_forecasts": xgboost_risk["daily_forecasts"],
    }


def generate_all_alerts(models, featured_df, prophet_df):
    """Generate alerts for ALL persons."""
    prophet_trend = get_prophet_trend(models, prophet_df)
    persons = featured_df["person_id"].unique()
    alerts = []
    
    for person_id in persons:
        xgboost_risk = get_xgboost_risk(models, featured_df, person_id)
        anomaly_status = get_anomaly_status(models, featured_df, person_id)
        exam_check = check_exam_absence(featured_df, person_id)
        
        alert = generate_person_alert(
            person_id, prophet_trend, xgboost_risk, anomaly_status, exam_check
        )
        alerts.append(alert)
    
    level_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda a: (level_order[a["alert_level"]], -a["combined_risk_score"]))
    
    return alerts, prophet_trend


def print_alert_dashboard(alerts, prophet_trend):
    """Print formatted alert dashboard."""
    print("\n" + "=" * 70)
    print("  ATTENDANCE ALERT DASHBOARD")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    trend_icon = {"DECLINING": "↘", "STABLE": "→", "IMPROVING": "↗", "UNKNOWN": "?"}
    print(f"\n  Group Trend: {trend_icon.get(prophet_trend['trend'], '')} "
          f"{prophet_trend['trend']}")
    if prophet_trend["current_rate"]:
        print(f"  Current Rate: {prophet_trend['current_rate']:.1%} → "
              f"Forecast: {prophet_trend['forecast_rate']:.1%}")
    
    level_counts = {}
    for alert in alerts:
        level_counts[alert["alert_level"]] = level_counts.get(alert["alert_level"], 0) + 1
    
    print(f"\n  Summary:")
    icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
    for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        print(f"    {icons.get(level, '')} {level}: {level_counts.get(level, 0)} persons")
    
    # Detailed: CRITICAL and HIGH
    actionable = [a for a in alerts if a["alert_level"] in ["CRITICAL", "HIGH"]]
    
    if actionable:
        print(f"\n" + "-" * 70)
        print("  PERSONS REQUIRING ATTENTION")
        print("-" * 70)
        
        for alert in actionable:
            icon = icons.get(alert["alert_level"], "")
            print(f"\n  {icon} {alert['person_id']} — {alert['alert_level']}")
            print(f"     Risk Score: {alert['combined_risk_score']:.0%}")
            print(f"     Predicted Absences: "
                  f"{alert['model_details']['xgboost']['predicted_absences_7d']}/7")
            
            if alert["anomaly_types"]:
                print(f"     Anomalies: {', '.join(alert['anomaly_types'])}")
            
            print(f"     Reasons:")
            for reason in alert["reasons"]:
                print(f"       - {reason}")
            
            print(f"     Actions:")
            for action in alert["recommended_actions"]:
                print(f"       → {action}")
            
            print(f"     7-Day Forecast:")
            for day in alert["daily_forecasts"]:
                bar = "█" * int(day["absence_probability"] * 20)
                print(f"       {day['date']}  {day['absence_probability']:5.1%}  "
                      f"{bar}  {day['predicted_status']}")
    
    # MEDIUM watch list
    medium = [a for a in alerts if a["alert_level"] == "MEDIUM"]
    if medium:
        print(f"\n" + "-" * 70)
        print(f"  WATCH LIST ({len(medium)} persons)")
        print("-" * 70)
        for alert in medium:
            anomaly_str = f"  [{', '.join(alert['anomaly_types'])}]" if alert["anomaly_types"] else ""
            print(f"    🟡 {alert['person_id']}  "
                  f"Risk: {alert['combined_risk_score']:.0%}  "
                  f"Absences: {alert['model_details']['xgboost']['predicted_absences_7d']}/7"
                  f"{anomaly_str}")
    
    print(f"\n  🟢 {level_counts.get('LOW', 0)} persons are LOW risk — no action needed")
    print("=" * 70)


def lookup_person(alerts, person_id):
    """Look up a specific person's alert."""
    for alert in alerts:
        if alert["person_id"] == person_id:
            return alert
    return None


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
if __name__ == "__main__":
    
    print("=" * 70)
    print("  LOADING MODELS & DATA")
    print("=" * 70)
    
    try:
        featured_df = pd.read_csv("featured_attendance_data.csv")
        featured_df["date"] = pd.to_datetime(featured_df["date"])
        raw_df = pd.read_csv("raw_attendance_data.csv")
        prophet_df = prepare_prophet_data(raw_df)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        exit(1)
    
    models = load_models()
    
    print("\nGenerating alerts for all persons...")
    alerts, prophet_trend = generate_all_alerts(models, featured_df, prophet_df)
    
    print_alert_dashboard(alerts, prophet_trend)
    
    # Individual lookup demo
    print("\n" + "=" * 70)
    print("  DEMO: INDIVIDUAL LOOKUP")
    print("=" * 70)
    
    top_alert = alerts[0]
    print(f"\n--- Highest risk: {top_alert['person_id']} ---")
    # print(json.dumps(top_alert, indent=2))
    print(json.dumps(top_alert, indent=2, default=str))
    
    # Save
    full_report = {
        "generated_at": datetime.now().isoformat(),
        "group_trend": prophet_trend,
        "anomaly_types_supported": [
            "SUDDEN_DROP", "EXAM_ABSENCE", "PERFECT_THEN_ABSENT",
            "ERRATIC_PATTERN", "PROLONGED_ABSENCE"
        ],
        "summary": {
            "total_persons": len(alerts),
            "critical": sum(1 for a in alerts if a["alert_level"] == "CRITICAL"),
            "high": sum(1 for a in alerts if a["alert_level"] == "HIGH"),
            "medium": sum(1 for a in alerts if a["alert_level"] == "MEDIUM"),
            "low": sum(1 for a in alerts if a["alert_level"] == "LOW"),
        },
        "alerts": alerts,
    }
    
    with open("alert_report.json", "w") as f:
        json.dump(full_report, f, indent=2, default=str)
    print(f"\nFull report saved: alert_report.json")
    
    print("\n" + "=" * 70)
    print("  ALERT SYSTEM v2 COMPLETE")
    print("=" * 70)