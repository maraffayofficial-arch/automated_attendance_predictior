"""
Real-time ML analysis service.
Analyzes individual persons without reprocessing entire dataset.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import os
import sys

# Add attendance_predictor to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'attendance_predictor'))

from prophet_model import (
    engineer_features,
    get_person_features,
    prepare_prophet_data,
    get_feature_columns,
    get_anomaly_columns,
    EXAM_PERIODS
)


class MLService:
    def __init__(self, db, models_dir=None):
        self.db = db
        if models_dir is None:
            models_dir = os.path.join(
                os.path.dirname(__file__),
                '..',
                'attendance_predictor',
                'models'
            )
        self.models = self._load_models(models_dir)
        self.group_trend_cache = None
        self.group_trend_updated = None

    def _load_models(self, models_dir):
        """Load trained models once at startup"""
        models = {}

        xgboost_path = os.path.join(models_dir, "xgboost_model.pkl")
        models["xgboost"] = joblib.load(xgboost_path)
        print(f"  [OK] XGBoost loaded from {xgboost_path}")

        iso_path = os.path.join(models_dir, "isolation_forest_model.pkl")
        iso_data = joblib.load(iso_path)
        models["isolation_forest"] = iso_data["model"]
        models["iso_scaler"] = iso_data["scaler"]
        print(f"  [OK] Isolation Forest loaded from {iso_path}")

        prophet_path = os.path.join(models_dir, "prophet_model.pkl")
        if os.path.exists(prophet_path):
            models["prophet"] = joblib.load(prophet_path)
            print(f"  [OK] Prophet loaded from {prophet_path}")
        else:
            models["prophet"] = None
            print(f"  [WARN] Prophet not found - group trends will be unavailable")

        return models

    def analyze_person(self, person_id):
        """
        Analyze a single person and update their prediction in database.
        This is FAST - only processes one person's data.
        """
        # Get person's attendance records
        records = list(self.db.attendance_records.find(
            {"person_id": person_id}
        ).sort("date", 1))

        if len(records) < 7:
            # Not enough data for meaningful prediction
            return self._store_insufficient_data(person_id, len(records))

        # Convert to DataFrame
        df = pd.DataFrame(records)

        # Engineer features for this person only
        try:
            featured_df = engineer_features(df)
        except Exception as e:
            print(f"Error engineering features for {person_id}: {e}")
            return self._store_error(person_id, str(e))

        # Get group trend (cached, updated once per day)
        prophet_trend = self._get_group_trend()

        # Run all 3 models
        try:
            xgboost_risk = self._get_xgboost_risk(featured_df, person_id)
            anomaly_status = self._get_anomaly_status(featured_df, person_id)
            exam_check = self._check_exam_absence(featured_df, person_id)

            # Generate alert
            alert = self._generate_person_alert(
                person_id, prophet_trend, xgboost_risk, anomaly_status, exam_check
            )

            # Store in database
            self._store_prediction(alert)

            return alert
        except Exception as e:
            print(f"Error analyzing {person_id}: {e}")
            return self._store_error(person_id, str(e))

    def analyze_multiple_persons(self, person_ids):
        """Analyze multiple persons (used after bulk import)"""
        results = []
        for person_id in person_ids:
            try:
                result = self.analyze_person(person_id)
                results.append(result)
            except Exception as e:
                print(f"Error analyzing {person_id}: {e}")
        return results

    def _get_group_trend(self):
        """Get group trend (cached for 24 hours)"""
        now = datetime.utcnow()

        # Return cached if less than 24 hours old
        if (self.group_trend_cache and self.group_trend_updated and
            (now - self.group_trend_updated).total_seconds() < 86400):
            return self.group_trend_cache

        # Recalculate group trend
        if self.models["prophet"]:
            all_records = list(self.db.attendance_records.find({}))
            if all_records:
                try:
                    df = pd.DataFrame(all_records)
                    prophet_df = prepare_prophet_data(df)

                    model = self.models["prophet"]
                    last_date = prophet_df["ds"].max()
                    future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=7)
                    future = pd.DataFrame({"ds": future_dates})
                    future["is_exam_period"] = 0

                    forecast = model.predict(future)
                    forecast["yhat"] = forecast["yhat"].clip(0, 1)

                    current_rate = prophet_df["y"].tail(7).mean()
                    forecast_rate = forecast["yhat"].mean()

                    if forecast_rate < current_rate - 0.03:
                        trend = "DECLINING"
                    elif forecast_rate > current_rate + 0.03:
                        trend = "IMPROVING"
                    else:
                        trend = "STABLE"

                    trend_data = {
                        "trend": trend,
                        "current_rate": round(float(current_rate), 4),
                        "forecast_rate": round(float(forecast_rate), 4),
                    }

                    # Cache it
                    self.group_trend_cache = trend_data
                    self.group_trend_updated = now

                    # Store in database for dashboard
                    self.db.group_trend_cache.update_one(
                        {"_id": "current"},
                        {"$set": {"trend": trend_data, "updated_at": now}},
                        upsert=True
                    )

                    return trend_data
                except Exception as e:
                    print(f"Error calculating group trend: {e}")

        return {"trend": "STABLE", "current_rate": None, "forecast_rate": None}

    def _get_xgboost_risk(self, featured_df, person_id):
        """Get XGBoost's individual risk with 7-day forecast."""
        feature_cols = get_feature_columns()
        model = self.models["xgboost"]

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

    def _get_anomaly_status(self, featured_df, person_id):
        """Get Isolation Forest's anomaly assessment."""
        anomaly_cols = get_anomaly_columns()
        model = self.models["isolation_forest"]
        scaler = self.models["iso_scaler"]

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

    def _check_exam_absence(self, featured_df, person_id):
        """Rule-based check: Exam Absence Detection."""
        person_data = get_person_features(featured_df, person_id)

        exam_days = person_data[person_data["is_exam_period"] == 1]

        if exam_days.empty:
            return {"has_exam_absence": False, "exam_absence_rate": 0, "exam_days_missed": 0}

        last_exam_end = exam_days["date"].max()
        last_exam_start = last_exam_end - pd.Timedelta(days=15)
        recent_exam = exam_days[exam_days["date"] >= last_exam_start]

        if recent_exam.empty:
            return {"has_exam_absence": False, "exam_absence_rate": 0, "exam_days_missed": 0}

        exam_absence_rate = 1 - recent_exam["attendance_binary"].mean()
        exam_days_missed = int((recent_exam["attendance_binary"] == 0).sum())
        total_exam_days = len(recent_exam)

        is_concerning = exam_absence_rate >= 0.30

        return {
            "has_exam_absence": is_concerning,
            "exam_absence_rate": round(float(exam_absence_rate), 4),
            "exam_days_missed": exam_days_missed,
            "total_exam_days": total_exam_days,
        }

    def _generate_person_alert(self, person_id, prophet_trend, xgboost_risk, anomaly_status, exam_check):
        """Combine all model outputs into a single alert."""
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

        reasons = []
        anomaly_types = []
        recommended_actions = []

        base_risk = xgboost_risk["current_absence_probability"]
        combined_risk = base_risk

        if anomaly_status["is_anomaly"]:
            atype = anomaly_status["anomaly_type"]
            combined_risk += 0.15
            anomaly_types.append(atype)
            reasons.append(ANOMALY_DESCRIPTIONS.get(atype, "Anomalous behavior detected"))
            recommended_actions.append(ANOMALY_ACTIONS.get(atype, "Monitor closely"))

        if exam_check["has_exam_absence"]:
            anomaly_types.append("EXAM_ABSENCE")
            combined_risk += 0.10
            reasons.append(
                f"Missed {exam_check['exam_days_missed']}/{exam_check['total_exam_days']} "
                f"exam days ({exam_check['exam_absence_rate']:.0%} absence rate during exams)"
            )
            recommended_actions.append(ANOMALY_ACTIONS["EXAM_ABSENCE"])

        if prophet_trend["trend"] == "DECLINING":
            combined_risk += 0.05
            reasons.append("Group attendance trend is declining")

        if xgboost_risk["predicted_absences_7d"] >= 4:
            reasons.append(f"Predicted absent {xgboost_risk['predicted_absences_7d']}/7 days next week")
            recommended_actions.append("Proactive outreach before absences accumulate")

        if base_risk >= 0.60:
            reasons.append(f"High absence probability: {base_risk:.0%}")
        elif base_risk >= 0.35:
            reasons.append(f"Moderate absence probability: {base_risk:.0%}")

        combined_risk = min(combined_risk, 1.0)

        if (combined_risk >= 0.8 or
            "PERFECT_THEN_ABSENT" in anomaly_types or
            "PROLONGED_ABSENCE" in anomaly_types or
            xgboost_risk["predicted_absences_7d"] >= 6):
            alert_level = "CRITICAL"
            if not recommended_actions:
                recommended_actions.append("Immediate intervention required")
        elif (combined_risk >= 0.60 or
              xgboost_risk["predicted_absences_7d"] >= 4 or
              "EXAM_ABSENCE" in anomaly_types):
            alert_level = "HIGH"
            if not recommended_actions:
                recommended_actions.append("Schedule meeting this week")
        elif combined_risk >= 0.35 or "ERRATIC_PATTERN" in anomaly_types:
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

    def _store_prediction(self, alert):
        """Store prediction in database"""
        alert["last_updated"] = datetime.utcnow()

        level_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        alert["alert_level_order"] = level_order[alert["alert_level"]]

        # Convert numpy types to Python native types for MongoDB
        alert = self._convert_numpy_types(alert)

        self.db.person_predictions.update_one(
            {"person_id": alert["person_id"]},
            {"$set": alert},
            upsert=True
        )

    def _convert_numpy_types(self, obj):
        """Recursively convert numpy types to Python native types"""
        if isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    def _store_insufficient_data(self, person_id, record_count):
        """Store placeholder for persons with insufficient data"""
        self.db.person_predictions.update_one(
            {"person_id": person_id},
            {"$set": {
                "person_id": person_id,
                "alert_level": "LOW",
                "alert_level_order": 3,
                "combined_risk_score": 0,
                "reasons": [f"Insufficient attendance data ({record_count} days, need at least 7)"],
                "recommended_actions": ["Continue recording attendance"],
                "anomaly_types": [],
                "last_updated": datetime.utcnow()
            }},
            upsert=True
        )
        return {"person_id": person_id, "status": "insufficient_data", "record_count": record_count}

    def _store_error(self, person_id, error_msg):
        """Store error status"""
        self.db.person_predictions.update_one(
            {"person_id": person_id},
            {"$set": {
                "person_id": person_id,
                "alert_level": "LOW",
                "alert_level_order": 3,
                "combined_risk_score": 0,
                "reasons": [f"Analysis error: {error_msg}"],
                "recommended_actions": ["Check data quality"],
                "anomaly_types": [],
                "last_updated": datetime.utcnow()
            }},
            upsert=True
        )
        return {"person_id": person_id, "status": "error", "error": error_msg}


# Global instance (initialized in app.py)
ml_service = None
