"""
==========================================================
 ADAPTIVE LEARNING SYSTEM
 
 This script handles MODEL RETRAINING as new attendance
 data accumulates over time. Models improve by learning
 from recent patterns.
 
 WHEN TO RUN:
   - Weekly (recommended) or monthly
   - After a significant event (new semester, policy change)
   - When alert accuracy starts declining
   
 WHAT IT DOES:
   1. Loads latest raw data from the database
   2. Re-runs feature engineering
   3. Retrains XGBoost on full updated dataset
   4. Retrains Isolation Forest on latest behavioral snapshots
   5. Saves new models (keeps old ones as backup)
   6. Logs retraining metrics for tracking improvement
   
 WHAT IT DOES NOT RETRAIN:
   - Prophet: retrain manually at semester boundaries
     (it needs at least 6+ months of data to be useful,
     retraining weekly would overfit to noise)
==========================================================
"""

import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import joblib
import json
import os
import shutil
from datetime import datetime

# from feature_engineering import (
#     engineer_features,
#     get_feature_columns,
#     get_anomaly_columns,
# )


# -------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------
CONFIG = {
    "models_dir": "models",
    "backup_dir": "models/backups",
    "logs_dir": "retraining_logs",
    
    # XGBoost
    "xgb_warmup_days": 30,         # skip first 30 days per person
    "xgb_n_estimators": 200,
    "xgb_max_depth": 5,
    "xgb_learning_rate": 0.1,
    
    # Isolation Forest
    "iso_contamination": 0.15,
    "iso_lookback_days": 20,       # use last 20 calendar days
    
    # Performance threshold
    "min_auc_threshold": 0.65,     # warn if AUC drops below this
}


def backup_existing_models(models_dir, backup_dir):
    """
    Save current models as backup before retraining.
    Backups are timestamped so you can rollback if needed.
    """
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backed_up = []
    for filename in os.listdir(models_dir):
        if filename.endswith(".pkl"):
            src = os.path.join(models_dir, filename)
            dst = os.path.join(backup_dir, f"{timestamp}_{filename}")
            shutil.copy2(src, dst)
            backed_up.append(filename)
    
    if backed_up:
        print(f"  Backed up {len(backed_up)} models to {backup_dir}/")
    return backed_up


def retrain_xgboost(featured_df, config):
    """
    Retrain XGBoost on the full updated dataset.
    Returns the new model and performance metrics.
    """
    print("\n" + "-" * 60)
    print("  RETRAINING XGBOOST")
    print("-" * 60)
    
    feature_cols = get_feature_columns()
    
    # Skip warmup period
    df = featured_df.copy()
    df["row_num"] = df.groupby("person_id").cumcount()
    df = df[df["row_num"] >= config["xgb_warmup_days"]].drop(columns=["row_num"])
    
    X = df[feature_cols]
    y = 1 - df["attendance_binary"]  # flip: 1 = absent
    
    print(f"  Training samples: {len(X)}")
    print(f"  Absence rate: {y.mean():.2%}")
    
    # Train with cross-validation for metrics
    model = XGBClassifier(
        n_estimators=config["xgb_n_estimators"],
        max_depth=config["xgb_max_depth"],
        learning_rate=config["xgb_learning_rate"],
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_alpha=0.1,
        reg_lambda=1.0,
        scale_pos_weight=(1 - y.mean()) / y.mean(),
        random_state=42,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    
    # Quick CV for metrics (3 folds for speed during retraining)
    tscv = TimeSeriesSplit(n_splits=3)
    cv_metrics = {"accuracy": [], "f1": [], "auc": []}
    
    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        
        y_pred = model.predict(X_val)
        y_prob = model.predict_proba(X_val)[:, 1]
        
        cv_metrics["accuracy"].append(accuracy_score(y_val, y_pred))
        cv_metrics["f1"].append(f1_score(y_val, y_pred, zero_division=0))
        cv_metrics["auc"].append(roc_auc_score(y_val, y_prob))
    
    avg_metrics = {k: round(float(np.mean(v)), 4) for k, v in cv_metrics.items()}
    print(f"  CV Accuracy: {avg_metrics['accuracy']:.4f}")
    print(f"  CV F1:       {avg_metrics['f1']:.4f}")
    print(f"  CV AUC:      {avg_metrics['auc']:.4f}")
    
    # Check for performance degradation
    if avg_metrics["auc"] < config["min_auc_threshold"]:
        print(f"  ⚠ WARNING: AUC ({avg_metrics['auc']}) below threshold "
              f"({config['min_auc_threshold']}). Model may need review.")
    
    # Final training on all data
    model.fit(X, y, verbose=False)
    
    # Save
    save_path = os.path.join(config["models_dir"], "xgboost_model.pkl")
    joblib.dump(model, save_path)
    print(f"  Model saved: {save_path}")
    
    return model, avg_metrics


def retrain_isolation_forest(featured_df, config):
    """
    Retrain Isolation Forest on latest behavioral snapshots.
    """
    print("\n" + "-" * 60)
    print("  RETRAINING ISOLATION FOREST")
    print("-" * 60)
    
    anomaly_cols = get_anomaly_columns()
    
    df = featured_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    
    max_date = df["date"].max()
    cutoff = max_date - pd.Timedelta(days=config["iso_lookback_days"])
    recent = df[df["date"] > cutoff]
    
    # Per-person summaries
    summaries = []
    for person_id, group in recent.groupby("person_id"):
        summary = {"person_id": person_id}
        for col in anomaly_cols:
            summary[col] = group[col].iloc[-1]
        summaries.append(summary)
    
    summary_df = pd.DataFrame(summaries)
    X = summary_df[anomaly_cols]
    
    print(f"  Persons analyzed: {len(X)}")
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = IsolationForest(
        n_estimators=200,
        contamination=config["iso_contamination"],
        max_samples="auto",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)
    
    predictions = model.predict(X_scaled)
    n_anomalies = (predictions == -1).sum()
    
    print(f"  Anomalies detected: {n_anomalies} ({n_anomalies/len(X):.0%})")
    
    # Save
    save_path = os.path.join(config["models_dir"], "isolation_forest_model.pkl")
    joblib.dump({"model": model, "scaler": scaler}, save_path)
    print(f"  Model saved: {save_path}")
    
    return model, scaler, {"anomalies_detected": int(n_anomalies), "total_persons": len(X)}


def log_retraining(xgb_metrics, iso_metrics, config):
    """
    Log retraining results for tracking model performance over time.
    Append to a JSON log file so you can monitor for drift.
    """
    os.makedirs(config["logs_dir"], exist_ok=True)
    log_path = os.path.join(config["logs_dir"], "retraining_history.json")
    
    # Load existing logs
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            history = json.load(f)
    else:
        history = []
    
    # Append new entry
    entry = {
        "timestamp": datetime.now().isoformat(),
        "xgboost": xgb_metrics,
        "isolation_forest": iso_metrics,
    }
    history.append(entry)
    
    with open(log_path, "w") as f:
        json.dump(history, f, indent=2, default=str)
    
    print(f"\n  Retraining log saved: {log_path}")
    print(f"  Total retraining sessions logged: {len(history)}")
    
    # Show performance trend if multiple entries
    if len(history) >= 2:
        prev_auc = history[-2]["xgboost"].get("auc", 0)
        curr_auc = xgb_metrics.get("auc", 0)
        diff = curr_auc - prev_auc
        
        if diff > 0:
            print(f"  AUC trend: {prev_auc:.4f} → {curr_auc:.4f} (↗ +{diff:.4f})")
        elif diff < 0:
            print(f"  AUC trend: {prev_auc:.4f} → {curr_auc:.4f} (↘ {diff:.4f})")
        else:
            print(f"  AUC trend: {prev_auc:.4f} → {curr_auc:.4f} (→ unchanged)")
    
    return history


def run_adaptive_learning(raw_data_path="raw_attendance_data.csv"):
    """
    Full adaptive learning pipeline.
    
    In production, your backend calls this function periodically
    (e.g., every Sunday night via a cron job).
    
    Parameters
    ----------
    raw_data_path : str
        Path to the latest raw data export from the database.
        Your backend team exports this before triggering retraining.
    """
    print("=" * 60)
    print("  ADAPTIVE LEARNING SYSTEM")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # --- Step 1: Load latest data ---
    print("\n[1/5] Loading latest data...")
    try:
        raw_df = pd.read_csv(raw_data_path)
        raw_df["date"] = pd.to_datetime(raw_df["date"])
    except FileNotFoundError:
        print(f"  ERROR: {raw_data_path} not found.")
        return None
    
    print(f"  Records: {len(raw_df)}")
    print(f"  Persons: {raw_df['person_id'].nunique()}")
    print(f"  Date range: {raw_df['date'].min()} to {raw_df['date'].max()}")
    
    # --- Step 2: Feature engineering ---
    print("\n[2/5] Running feature engineering...")
    featured_df = engineer_features(raw_df)
    print(f"  Featured records: {len(featured_df)}")
    print(f"  Features: {len(featured_df.columns)} columns")
    
    # --- Step 3: Backup existing models ---
    print("\n[3/5] Backing up current models...")
    backup_existing_models(CONFIG["models_dir"], CONFIG["backup_dir"])
    
    # --- Step 4: Retrain models ---
    print("\n[4/5] Retraining models...")
    xgb_model, xgb_metrics = retrain_xgboost(featured_df, CONFIG)
    iso_model, iso_scaler, iso_metrics = retrain_isolation_forest(featured_df, CONFIG)
    
    # --- Step 5: Log results ---
    print("\n[5/5] Logging retraining results...")
    history = log_retraining(xgb_metrics, iso_metrics, CONFIG)
    
    # --- Save updated featured data ---
    featured_df.to_csv("featured_attendance_data.csv", index=False)
    
    print("\n" + "=" * 60)
    print("  ADAPTIVE LEARNING COMPLETE")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return {
        "xgboost_metrics": xgb_metrics,
        "isolation_forest_metrics": iso_metrics,
        "retraining_count": len(history),
    }


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
if __name__ == "__main__":
    result = run_adaptive_learning("raw_attendance_data.csv")
    
    if result:
        print("\n--- Summary ---")
        print(f"  XGBoost AUC:        {result['xgboost_metrics']['auc']:.4f}")
        print(f"  XGBoost F1:         {result['xgboost_metrics']['f1']:.4f}")
        print(f"  IF Anomalies:       {result['isolation_forest_metrics']['anomalies_detected']}")
        print(f"  Retraining count:   {result['retraining_count']}")