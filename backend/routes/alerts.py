from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from datetime import datetime
from config import ML_DIR
import subprocess
import sys
import json
import csv
import os

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/", methods=["GET"])
@jwt_required()
def get_alerts():
    db = current_app.db
    level = request.args.get("level", "").upper()

    run = db.alert_runs.find_one(sort=[("generated_at", -1)])
    if not run:
        return jsonify({"error": "No alert data yet. Run the ML pipeline first."}), 404

    run["_id"] = str(run["_id"])
    if isinstance(run.get("generated_at"), datetime):
        run["generated_at"] = run["generated_at"].isoformat()

    if level and level != "ALL":
        run["alerts"] = [a for a in run.get("alerts", []) if a.get("alert_level") == level]

    return jsonify(run)


@alerts_bp.route("/person/<person_id>", methods=["GET"])
@jwt_required()
def get_person_alert(person_id):
    db = current_app.db
    run = db.alert_runs.find_one(sort=[("generated_at", -1)])
    if not run:
        return jsonify({"error": "No alert data available"}), 404

    alert = next(
        (a for a in run.get("alerts", []) if a.get("person_id") == person_id), None
    )
    if not alert:
        return jsonify({"error": "No alert found for this person"}), 404

    return jsonify(alert)


@alerts_bp.route("/run", methods=["POST"])
@jwt_required()
def run_pipeline():
    db = current_app.db

    records = list(db.attendance_records.find({}, {"_id": 0, "created_at": 0}))
    if not records:
        return jsonify({"error": "No attendance records found. Add records before running analysis."}), 400

    # Export records to CSV for ML pipeline
    csv_path = os.path.join(ML_DIR, "raw_attendance_data.csv")
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["person_id", "date", "attendance_binary", "is_exam_period"]
            )
            writer.writeheader()
            writer.writerows(records)
    except Exception as e:
        return jsonify({"error": f"Failed to write CSV: {str(e)}"}), 500

    utf8_env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

    # Step 1 — feature engineering (prophet_model.py is the actual feature engineering script)
    try:
        fe = subprocess.run(
            [sys.executable, "prophet_model.py"],
            cwd=ML_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=utf8_env,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Feature engineering timed out (>5 min)"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to run feature engineering: {str(e)}"}), 500

    if fe.returncode != 0:
        return jsonify({"error": "Feature engineering failed", "details": fe.stderr[-2000:]}), 500

    # Step 2 — alert system (runs all 3 models, generates alert_report.json)
    try:
        result = subprocess.run(
            [sys.executable, "adaptive_learning.py"],
            cwd=ML_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=utf8_env,
            timeout=480,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "ML pipeline timed out (>8 min)"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to run alert system: {str(e)}"}), 500

    if result.returncode != 0:
        return jsonify({"error": "ML pipeline failed", "details": result.stderr[-2000:]}), 500

    # Read and store generated alert report
    report_path = os.path.join(ML_DIR, "alert_report.json")
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Failed to read alert report: {str(e)}"}), 500

    report["generated_at"] = datetime.utcnow()
    report["source"] = "pipeline_run"
    db.alert_runs.insert_one(report)

    return jsonify({
        "message": "Analysis complete",
        "summary": report.get("summary"),
        "group_trend": report.get("group_trend"),
    })


@alerts_bp.route("/import", methods=["POST"])
@jwt_required()
def import_existing_report():
    """Import the already-generated alert_report.json into MongoDB."""
    db = current_app.db
    report_path = os.path.join(ML_DIR, "alert_report.json")

    if not os.path.exists(report_path):
        return jsonify({"error": "alert_report.json not found in ML directory"}), 404

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Failed to read report: {str(e)}"}), 500

    report["imported_at"] = datetime.utcnow()
    report["source"] = "imported"
    if "generated_at" not in report:
        report["generated_at"] = datetime.utcnow()
    else:
        report["generated_at"] = datetime.utcnow()

    db.alert_runs.insert_one(report)

    return jsonify({
        "message": "Alert report imported successfully",
        "summary": report.get("summary"),
        "group_trend": report.get("group_trend"),
    })


@alerts_bp.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    db = current_app.db
    runs = list(
        db.alert_runs.find({}, {"alerts": 0}).sort("generated_at", -1).limit(20)
    )
    for r in runs:
        r["_id"] = str(r["_id"])
        if isinstance(r.get("generated_at"), datetime):
            r["generated_at"] = r["generated_at"].isoformat()
        if isinstance(r.get("imported_at"), datetime):
            r["imported_at"] = r["imported_at"].isoformat()
    return jsonify(runs)
