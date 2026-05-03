"""
==========================================================
 MODEL 1: PROPHET — Group-Level Attendance Trend Forecaster
 
 WHAT IT DOES:
   Forecasts the overall attendance RATE for the next 7 days
   at the department/class/organization level.
   
 WHY IT'S FIRST IN THE PIPELINE:
   It provides macro context. If Prophet says "overall attendance
   will drop to 68% next week," that context feeds into the
   alert system alongside individual predictions from XGBoost.
   
 INPUT:  Daily aggregated attendance rate (from feature_engineering.py)
 OUTPUT: 7-day forecast of daily attendance rates + trend direction
==========================================================
"""

import pandas as pd
import numpy as np
from prophet import Prophet
import matplotlib.pyplot as plt
import joblib
import warnings
import json
import os
from datetime import datetime

warnings.filterwarnings("ignore")


def train_prophet_model(
    prophet_df: pd.DataFrame,
    save_path: str = "models/prophet_model.pkl"
) -> Prophet:
    """
    Train Prophet on daily attendance rates.
    
    Parameters
    ----------
    prophet_df : pd.DataFrame
        Must have columns: 'ds' (date), 'y' (attendance rate), 'is_exam_period'
    save_path : str
        Where to save the trained model.
    
    Returns
    -------
    Prophet
        Trained model object.
    """
    print("=" * 60)
    print("  TRAINING PROPHET MODEL")
    print("=" * 60)
    
    model = Prophet(
        weekly_seasonality=True,
        yearly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.1,
        interval_width=0.90,
    )
    
    # Exam period as external regressor
    model.add_regressor("is_exam_period")
    
    print(f"Training data: {len(prophet_df)} days")
    print(f"Date range: {prophet_df['ds'].min()} to {prophet_df['ds'].max()}")
    print(f"Mean attendance rate: {prophet_df['y'].mean():.2%}")
    
    model.fit(prophet_df)
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    joblib.dump(model, save_path)
    print(f"\nModel saved to: {save_path}")
    
    return model


def forecast_7_days(
    model: Prophet,
    prophet_df: pd.DataFrame,
    exam_schedule: dict = None
) -> tuple:
    """
    Forecast attendance rate for the next 7 business days.
    
    Parameters
    ----------
    model : Prophet
        Trained Prophet model.
    prophet_df : pd.DataFrame
        Historical data (to determine the last known date).
    exam_schedule : dict, optional
        Mapping of date strings to is_exam_period (0 or 1).
    
    Returns
    -------
    tuple
        (forecast_df, current_rate, forecast_rate)
    """
    last_date = prophet_df["ds"].max()
    future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=7)
    future = pd.DataFrame({"ds": future_dates})
    
    if exam_schedule:
        future["is_exam_period"] = future["ds"].dt.strftime("%Y-%m-%d").map(
            exam_schedule
        ).fillna(0).astype(int)
    else:
        future["is_exam_period"] = 0
    
    forecast = model.predict(future)
    
    # Clip to valid range [0, 1]
    forecast["yhat"] = forecast["yhat"].clip(0, 1)
    forecast["yhat_lower"] = forecast["yhat_lower"].clip(0, 1)
    forecast["yhat_upper"] = forecast["yhat_upper"].clip(0, 1)
    
    current_rate = prophet_df["y"].tail(7).mean()
    forecast_rate = forecast["yhat"].mean()
    
    if forecast_rate < current_rate - 0.03:
        trend = "DECLINING"
    elif forecast_rate > current_rate + 0.03:
        trend = "IMPROVING"
    else:
        trend = "STABLE"
    
    forecast["trend_direction"] = trend
    
    result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper", "trend_direction"]].copy()
    result.columns = ["date", "predicted_rate", "lower_bound", "upper_bound", "trend"]
    
    return result, current_rate, forecast_rate


def plot_forecast(prophet_df: pd.DataFrame, forecast_result: pd.DataFrame):
    """Generate a visualization of historical data + forecast."""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    recent = prophet_df.tail(60)
    ax.plot(recent["ds"], recent["y"], color="#2196F3", alpha=0.7,
            label="Historical Rate", linewidth=1.5)
    
    ax.plot(forecast_result["date"], forecast_result["predicted_rate"],
            color="#FF5722", linewidth=2.5, label="Forecast", marker="o")
    
    ax.fill_between(
        forecast_result["date"],
        forecast_result["lower_bound"],
        forecast_result["upper_bound"],
        alpha=0.2, color="#FF5722", label="90% Confidence"
    )
    
    ax.axvline(x=recent["ds"].iloc[-1], color="gray", linestyle="--", alpha=0.5)
    
    ax.set_title("Prophet: 7-Day Attendance Rate Forecast", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Attendance Rate")
    ax.legend()
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("prophet_forecast_plot.png", dpi=150, bbox_inches="tight")
    print("Plot saved: prophet_forecast_plot.png")
    plt.close()


def generate_prophet_report(
    forecast_result: pd.DataFrame,
    current_rate: float,
    forecast_rate: float
) -> dict:
    """
    Generate a structured report from Prophet's forecast.
    This gets passed to the alert system later.
    """
    report = {
        "model": "Prophet",
        "generated_at": datetime.now().isoformat(),
        "current_7d_avg_rate": round(current_rate, 4),
        "forecast_7d_avg_rate": round(forecast_rate, 4),
        "trend": forecast_result["trend"].iloc[0],
        "daily_forecasts": [],
    }
    
    for _, row in forecast_result.iterrows():
        report["daily_forecasts"].append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "predicted_rate": round(row["predicted_rate"], 4),
            "lower_bound": round(row["lower_bound"], 4),
            "upper_bound": round(row["upper_bound"], 4),
        })
    
    return report


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
if __name__ == "__main__":
    
    try:
        prophet_df = pd.read_csv("prophet_ready_data.csv")
        prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
    except FileNotFoundError:
        print("ERROR: prophet_ready_data.csv not found.")
        print("Run these first:")
        print("  python generate_synthetic_data.py")
        print("  python feature_engineering.py")
        exit(1)
    
    # Train
    model = train_prophet_model(prophet_df)
    
    # Forecast
    print("\n" + "=" * 60)
    print("  7-DAY FORECAST")
    print("=" * 60)
    
    forecast_result, current_rate, forecast_rate = forecast_7_days(model, prophet_df)
    
    print(f"\nCurrent 7-day avg attendance rate:  {current_rate:.2%}")
    print(f"Forecast 7-day avg attendance rate: {forecast_rate:.2%}")
    print(f"Trend: {forecast_result['trend'].iloc[0]}")
    print(f"\nDaily Forecasts:")
    print(forecast_result.to_string(index=False))
    
    # Plot
    plot_forecast(prophet_df, forecast_result)
    
    # Report
    report = generate_prophet_report(forecast_result, current_rate, forecast_rate)
    with open("prophet_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: prophet_report.json")
    
    print("\n" + "=" * 60)
    print("  PROPHET MODEL COMPLETE")
    print("=" * 60)