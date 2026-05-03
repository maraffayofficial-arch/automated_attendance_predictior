"""
==========================================================
 MODEL 2: XGBOOST — Individual Attendance Risk Predictor
 
 WHAT IT DOES:
   Predicts the probability of a specific person being ABSENT
   on a given day, based on their behavioral features.
   
 WHY IT'S THE CORE MODEL:
   Prophet tells you "the group trend is declining."
   XGBoost tells you "Raffay specifically has a 73% chance
   of being absent tomorrow." This is actionable.
   
 INPUT:  Feature-engineered data (from feature_engineering.py)
         11 features per person per day
 OUTPUT: Absence probability (0.0 to 1.0) per person per day
         + 7-day recursive forecast
         + feature importance ranking
==========================================================
"""

import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, classification_report,
    confusion_matrix
)
import matplotlib.pyplot as plt
import joblib
import json
import os
from datetime import datetime

# Import feature column definitions from your pipeline
# from feature_engineering import (
#     engineer_features,
#     get_feature_columns,
#     get_person_features,
#     _compute_workload_indicator,
#     EXAM_PERIODS
# )


def prepare_training_data(featured_df: pd.DataFrame):
    """
    Prepare X (features) and y (target) for XGBoost.
    
    IMPORTANT: We skip the first 30 days per person because
    rolling_avg_30d needs 30 days of history to be meaningful.
    Training on incomplete rolling features would teach the
    model wrong patterns.
    
    Parameters
    ----------
    featured_df : pd.DataFrame
        Output of engineer_features()
    
    Returns
    -------
    tuple
        (X, y, filtered_df) — features, target, and the filtered dataframe
    """
    feature_cols = get_feature_columns()
    
    # Skip first 30 days per person (rolling features need warmup)
    df = featured_df.copy()
    df["row_num"] = df.groupby("person_id").cumcount()
    df = df[df["row_num"] >= 30].drop(columns=["row_num"])
    
    X = df[feature_cols].copy()
    y = df["attendance_binary"].copy()
    
    # XGBoost predicts ABSENCE risk, so flip the target:
    # 1 = absent (risk), 0 = present (safe)
    y = 1 - y
    
    return X, y, df


def train_xgboost_model(
    X: pd.DataFrame,
    y: pd.Series,
    save_path: str = "models/xgboost_model.pkl"
) -> XGBClassifier:
    """
    Train XGBoost with time-series aware cross-validation.
    
    We use TimeSeriesSplit (not random KFold) because attendance
    data is temporal — you can't use future data to predict the past.
    """
    print("=" * 60)
    print("  TRAINING XGBOOST MODEL")
    print("=" * 60)
    
    print(f"Training samples: {len(X)}")
    print(f"Features: {list(X.columns)}")
    print(f"Absence rate (target=1): {y.mean():.2%}")
    
    # --- Model configuration ---
    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_alpha=0.1,       # L1 regularization
        reg_lambda=1.0,      # L2 regularization
        scale_pos_weight=(1 - y.mean()) / y.mean(),  # handle class imbalance
        random_state=42,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    
    # --- Time-Series Cross Validation ---
    print("\nRunning TimeSeriesSplit cross-validation (5 folds)...")
    tscv = TimeSeriesSplit(n_splits=5)
    
    cv_results = {
        "accuracy": [], "precision": [], "recall": [],
        "f1": [], "roc_auc": []
    }
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        y_pred = model.predict(X_val)
        y_prob = model.predict_proba(X_val)[:, 1]
        
        cv_results["accuracy"].append(accuracy_score(y_val, y_pred))
        cv_results["precision"].append(precision_score(y_val, y_pred, zero_division=0))
        cv_results["recall"].append(recall_score(y_val, y_pred, zero_division=0))
        cv_results["f1"].append(f1_score(y_val, y_pred, zero_division=0))
        cv_results["roc_auc"].append(roc_auc_score(y_val, y_prob))
        
        print(f"  Fold {fold}: Accuracy={cv_results['accuracy'][-1]:.4f}  "
              f"F1={cv_results['f1'][-1]:.4f}  "
              f"AUC={cv_results['roc_auc'][-1]:.4f}")
    
    print(f"\n--- Cross-Validation Averages ---")
    for metric, values in cv_results.items():
        print(f"  {metric:>10s}: {np.mean(values):.4f} (±{np.std(values):.4f})")
    
    # --- Final training on ALL data ---
    print("\nTraining final model on full dataset...")
    model.fit(X, y, verbose=False)
    
    # --- Save ---
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    joblib.dump(model, save_path)
    print(f"Model saved to: {save_path}")
    
    return model, cv_results


def get_feature_importance(model: XGBClassifier, feature_cols: list) -> pd.DataFrame:
    """
    Extract and display feature importance ranking.
    This tells you WHICH features matter most for prediction.
    """
    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    
    importance["rank"] = range(1, len(importance) + 1)
    importance["importance_pct"] = (
        importance["importance"] / importance["importance"].sum() * 100
    ).round(2)
    
    return importance


def plot_feature_importance(importance: pd.DataFrame):
    """Plot feature importance as horizontal bar chart."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    imp_sorted = importance.sort_values("importance", ascending=True)
    
    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(imp_sorted)))
    
    ax.barh(imp_sorted["feature"], imp_sorted["importance"], color=colors)
    ax.set_xlabel("Importance Score")
    ax.set_title("XGBoost: Feature Importance for Absence Prediction",
                 fontsize=13, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("xgboost_feature_importance.png", dpi=150, bbox_inches="tight")
    print("Plot saved: xgboost_feature_importance.png")
    plt.close()


def predict_person_risk(
    model: XGBClassifier,
    featured_df: pd.DataFrame,
    person_id: str
) -> dict:
    """
    Get the current absence risk score for a specific person.
    
    This answers: "What is Raffay's risk of being absent TODAY?"
    """
    feature_cols = get_feature_columns()
    person_data = get_person_features(featured_df, person_id)
    
    # Use the latest row (most recent features)
    latest = person_data.iloc[-1:]
    X = latest[feature_cols]
    
    absence_prob = model.predict_proba(X)[0][1]
    risk_label = (
        "HIGH" if absence_prob >= 0.6
        else "MEDIUM" if absence_prob >= 0.35
        else "LOW"
    )
    
    return {
        "person_id": person_id,
        "date": str(latest["date"].values[0])[:10],
        "absence_probability": round(float(absence_prob), 4),
        "risk_level": risk_label,
        "current_features": {
            col: round(float(latest[col].values[0]), 4)
            for col in feature_cols
        }
    }


def forecast_7_days_individual(
    model: XGBClassifier,
    featured_df: pd.DataFrame,
    person_id: str
) -> dict:
    """
    RECURSIVE 7-DAY FORECAST for one person.
    
    How it works:
      Day 1: Use current features → predict → get probability
      Day 2: UPDATE features based on Day 1 prediction → predict again
      Day 3: UPDATE features based on Day 1+2 → predict again
      ... and so on for 7 days.
    
    The key insight: each prediction changes the features for the
    next prediction (rolling averages shift, consecutive absences
    may increment, trend changes).
    """
    feature_cols = get_feature_columns()
    person_data = get_person_features(featured_df, person_id)
    
    # Get the person's recent attendance history (need last 30 days)
    recent_attendance = list(person_data["attendance_binary"].tail(30).values)
    last_date = pd.to_datetime(person_data["date"].iloc[-1])
    
    # Person's historical mean and std (for z-score)
    person_mean = person_data["attendance_binary"].mean()
    person_std = person_data["attendance_binary"].std()
    if person_std == 0:
        person_std = 1  # avoid division by zero
    
    daily_forecasts = []
    
    # Get upcoming business days
    forecast_dates = pd.bdate_range(
        start=last_date + pd.Timedelta(days=1), periods=7
    )
    
    for forecast_date in forecast_dates:
        # --- Build feature vector for this day ---
        
        # Time features
        month = forecast_date.month
        day_of_week = forecast_date.dayofweek
        
        # Exam period check
        is_exam = 0
        for s, e in EXAM_PERIODS:
            if pd.Timestamp(s) <= forecast_date <= pd.Timestamp(e):
                is_exam = 1
                break
        
        # Workload indicator
        exam_starts = [pd.Timestamp(s) for s, e in EXAM_PERIODS]
        if is_exam:
            workload = 9.0
        else:
            future_exams = [s for s in exam_starts if s > forecast_date]
            if future_exams:
                days_to_exam = (future_exams[0] - forecast_date).days
            else:
                days_to_exam = 999
            
            if days_to_exam <= 7:
                workload = 7.0
            elif days_to_exam <= 14:
                workload = 6.0
            elif days_to_exam <= 21:
                workload = 5.0
            else:
                workload = 4.0
            
            if month in [5, 11, 12]:
                workload = min(workload + 1.0, 10.0)
            if month in [1, 8, 9] and days_to_exam > 21:
                workload = max(workload - 1.0, 2.0)
        
        # Rolling averages from recent attendance
        last_7 = recent_attendance[-7:]
        last_30 = recent_attendance[-30:]
        rolling_avg_7d = np.mean(last_7)
        rolling_avg_30d = np.mean(last_30)
        prev_7d = sum(last_7)
        prev_30d = sum(last_30)
        
        # Consecutive absences
        consec = 0
        for val in reversed(recent_attendance):
            if val == 0:
                consec += 1
            else:
                break
        
        # Z-score deviation
        z_score = (rolling_avg_7d - person_mean) / person_std
        
        # Attendance trend (slope of last 14 days)
        last_14 = recent_attendance[-14:]
        if len(last_14) >= 3:
            x = np.arange(len(last_14))
            trend = np.polyfit(x, last_14, 1)[0]
        else:
            trend = 0.0
        
        # Attendance variance (14-day) — high = erratic pattern
        variance_14d = np.var(last_14) if len(last_14) >= 3 else 0.0
        
        # Short-long average gap — positive = recent drop from history
        short_long_gap = rolling_avg_30d - rolling_avg_7d
        
        # --- Assemble feature vector ---
        feature_vector = pd.DataFrame([{
            "month": month,
            "day_of_week": day_of_week,
            "workload_indicator": workload,
            "is_exam_period": is_exam,
            "rolling_avg_7d": rolling_avg_7d,
            "rolling_avg_30d": rolling_avg_30d,
            "prev_7d_attendance": prev_7d,
            "prev_30d_attendance": prev_30d,
            "consecutive_absences": consec,
            "z_score_deviation": z_score,
            "attendance_trend": trend,
            "attendance_variance_14d": variance_14d,
            "short_long_avg_gap": short_long_gap,
        }])
        
        # Ensure column order matches training
        feature_vector = feature_vector[feature_cols]
        
        # --- Predict ---
        absence_prob = model.predict_proba(feature_vector)[0][1]
        predicted_absent = 1 if absence_prob >= 0.5 else 0
        predicted_attendance = 1 - predicted_absent  # flip back
        
        daily_forecasts.append({
            "date": forecast_date.strftime("%Y-%m-%d"),
            "absence_probability": round(float(absence_prob), 4),
            "predicted_status": "ABSENT" if predicted_absent else "PRESENT",
            "risk_level": (
                "HIGH" if absence_prob >= 0.6
                else "MEDIUM" if absence_prob >= 0.35
                else "LOW"
            ),
        })
        
        # --- Update history for next day's prediction ---
        # This is the RECURSIVE part: the prediction feeds into
        # the next day's features
        recent_attendance.append(predicted_attendance)
    
    # --- Summary ---
    predicted_absences = sum(
        1 for d in daily_forecasts if d["predicted_status"] == "ABSENT"
    )
    avg_risk = np.mean([d["absence_probability"] for d in daily_forecasts])
    
    overall_risk = (
        "HIGH" if avg_risk >= 0.6 or predicted_absences >= 4
        else "MEDIUM" if avg_risk >= 0.35 or predicted_absences >= 2
        else "LOW"
    )
    
    return {
        "person_id": person_id,
        "forecast_period": f"{forecast_dates[0].strftime('%Y-%m-%d')} to "
                          f"{forecast_dates[-1].strftime('%Y-%m-%d')}",
        "predicted_absences_count": predicted_absences,
        "predicted_present_count": 7 - predicted_absences,
        "average_absence_risk": round(float(avg_risk), 4),
        "overall_risk_level": overall_risk,
        "daily_forecasts": daily_forecasts,
    }


def evaluate_on_holdout(
    model: XGBClassifier,
    featured_df: pd.DataFrame,
    holdout_days: int = 30
) -> dict:
    """
    Evaluate model on the last N days of data (held out from training).
    This gives a realistic estimate of production performance.
    """
    feature_cols = get_feature_columns()
    
    # Use last holdout_days as test set
    df = featured_df.copy()
    df["row_num"] = df.groupby("person_id").cumcount()
    df = df[df["row_num"] >= 30].drop(columns=["row_num"])
    
    cutoff = df["date"].max() - pd.Timedelta(days=holdout_days)
    test_df = df[df["date"] > cutoff]
    
    X_test = test_df[feature_cols]
    y_test = 1 - test_df["attendance_binary"]  # flip: 1=absent
    
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    results = {
        "holdout_days": holdout_days,
        "test_samples": len(X_test),
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, y_prob), 4),
    }
    
    return results


def plot_risk_distribution(model, featured_df):
    """
    Plot the risk score distribution across all persons
    based on their latest features.
    """
    feature_cols = get_feature_columns()
    persons = featured_df["person_id"].unique()
    
    risks = []
    for pid in persons:
        person_data = featured_df[featured_df["person_id"] == pid]
        latest = person_data.iloc[-1:]
        X = latest[feature_cols]
        prob = model.predict_proba(X)[0][1]
        risks.append({"person_id": pid, "absence_risk": prob})
    
    risk_df = pd.DataFrame(risks).sort_values("absence_risk", ascending=False)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = ["#f44336" if r >= 0.6 else "#ff9800" if r >= 0.35 else "#4caf50"
              for r in risk_df["absence_risk"]]
    
    ax.bar(range(len(risk_df)), risk_df["absence_risk"], color=colors, width=0.8)
    
    ax.axhline(y=0.6, color="#f44336", linestyle="--", alpha=0.7, label="High Risk (≥0.6)")
    ax.axhline(y=0.35, color="#ff9800", linestyle="--", alpha=0.7, label="Medium Risk (≥0.35)")
    
    ax.set_xlabel("Persons (sorted by risk)")
    ax.set_ylabel("Absence Probability")
    ax.set_title("XGBoost: Current Risk Distribution Across All Persons",
                 fontsize=13, fontweight="bold")
    ax.legend()
    ax.set_ylim(0, 1)
    ax.grid(True, axis="y", alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("xgboost_risk_distribution.png", dpi=150, bbox_inches="tight")
    print("Plot saved: xgboost_risk_distribution.png")
    plt.close()
    
    # Print high risk persons
    high_risk = risk_df[risk_df["absence_risk"] >= 0.6]
    medium_risk = risk_df[(risk_df["absence_risk"] >= 0.35) & (risk_df["absence_risk"] < 0.6)]
    low_risk = risk_df[risk_df["absence_risk"] < 0.35]
    
    print(f"\nRisk Summary:")
    print(f"  HIGH risk:   {len(high_risk)} persons")
    print(f"  MEDIUM risk: {len(medium_risk)} persons")
    print(f"  LOW risk:    {len(low_risk)} persons")
    
    return risk_df


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
if __name__ == "__main__":
    
    # --- Step 1: Load featured data ---
    try:
        featured_df = pd.read_csv("featured_attendance_data.csv")
        featured_df["date"] = pd.to_datetime(featured_df["date"])
    except FileNotFoundError:
        print("ERROR: featured_attendance_data.csv not found.")
        print("Run these first:")
        print("  python generate_synthetic_data.py")
        print("  python feature_engineering.py")
        exit(1)
    
    # --- Step 2: Prepare training data ---
    X, y, filtered_df = prepare_training_data(featured_df)
    
    # --- Step 3: Train ---
    model, cv_results = train_xgboost_model(X, y)
    
    # --- Step 4: Feature importance ---
    print("\n" + "=" * 60)
    print("  FEATURE IMPORTANCE")
    print("=" * 60)
    
    importance = get_feature_importance(model, get_feature_columns())
    print(importance[["rank", "feature", "importance_pct"]].to_string(index=False))
    plot_feature_importance(importance)
    
    # --- Step 5: Holdout evaluation ---
    print("\n" + "=" * 60)
    print("  HOLDOUT EVALUATION (last 30 days)")
    print("=" * 60)
    
    holdout_results = evaluate_on_holdout(model, featured_df, holdout_days=30)
    for metric, value in holdout_results.items():
        print(f"  {metric:>15s}: {value}")
    
    # --- Step 6: Risk distribution ---
    print("\n" + "=" * 60)
    print("  RISK DISTRIBUTION")
    print("=" * 60)
    
    risk_df = plot_risk_distribution(model, featured_df)
    
    # --- Step 7: Demo — forecast for a specific person ---
    print("\n" + "=" * 60)
    print("  DEMO: 7-DAY FORECAST FOR A SPECIFIC PERSON")
    print("=" * 60)
    
    # Pick one high-risk and one low-risk person for demo
    demo_persons = [
        risk_df.iloc[0]["person_id"],   # highest risk
        risk_df.iloc[-1]["person_id"],  # lowest risk
    ]
    
    for pid in demo_persons:
        print(f"\n--- Forecast: {pid} ---")
        forecast = forecast_7_days_individual(model, featured_df, pid)
        
        print(f"  Period: {forecast['forecast_period']}")
        print(f"  Predicted absences: {forecast['predicted_absences_count']}/7")
        print(f"  Average risk: {forecast['average_absence_risk']:.2%}")
        print(f"  Overall risk level: {forecast['overall_risk_level']}")
        print(f"  Daily breakdown:")
        for day in forecast["daily_forecasts"]:
            print(f"    {day['date']}  |  {day['absence_probability']:.2%}  |  "
                  f"{day['predicted_status']:7s}  |  {day['risk_level']}")
    
    # --- Save report ---
    report = {
        "model": "XGBoost",
        "generated_at": datetime.now().isoformat(),
        "cv_results": {k: round(float(np.mean(v)), 4) for k, v in cv_results.items()},
        "holdout_results": holdout_results,
        "feature_importance": importance[["rank", "feature", "importance_pct"]].to_dict("records"),
    }
    
    with open("xgboost_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: xgboost_report.json")
    
    print("\n" + "=" * 60)
    print("  XGBOOST MODEL COMPLETE")
    print("=" * 60)