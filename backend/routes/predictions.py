from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from datetime import datetime
from middleware import get_user_role, get_user_department, can_access_all_departments, get_user_person_id

predictions_bp = Blueprint("predictions", __name__)


def serialize(doc):
    """Serialize MongoDB document"""
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("last_updated"), datetime):
        doc["last_updated"] = doc["last_updated"].isoformat()
    return doc


@predictions_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_predictions():
    """
    Get all person predictions (replaces /alerts endpoint for dashboard).
    Returns data in same format as old alerts endpoint for compatibility.
    Filters by department for teachers.
    """
    db = current_app.db

    # Build query based on user role and department
    query = {}

    if not can_access_all_departments():
        # Teachers only see their department
        user_dept = get_user_department()
        if user_dept:
            # Get person IDs from this department
            dept_persons = list(db.persons.find(
                {"department": user_dept},
                {"person_id": 1}
            ))
            dept_person_ids = [p["person_id"] for p in dept_persons]

            if dept_person_ids:
                query["person_id"] = {"$in": dept_person_ids}
            else:
                # No persons in this department
                return jsonify({
                    "generated_at": datetime.utcnow().isoformat(),
                    "alerts": [],
                    "summary": {"total_persons": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
                    "group_trend": {"trend": "STABLE", "current_rate": None, "forecast_rate": None},
                    "source": "real_time_predictions"
                })

    # Get predictions sorted by alert level
    predictions = list(
        db.person_predictions.find(query).sort("alert_level_order", 1)
    )

    if not predictions:
        return jsonify({"error": "No predictions available. Add attendance data and wait for analysis."}), 404

    # Calculate summary
    summary = {
        "total_persons": len(predictions),
        "critical": sum(1 for p in predictions if p.get("alert_level") == "CRITICAL"),
        "high": sum(1 for p in predictions if p.get("alert_level") == "HIGH"),
        "medium": sum(1 for p in predictions if p.get("alert_level") == "MEDIUM"),
        "low": sum(1 for p in predictions if p.get("alert_level") == "LOW"),
    }

    # Get cached group trend
    group_trend_doc = db.group_trend_cache.find_one({"_id": "current"})
    if group_trend_doc and "trend" in group_trend_doc:
        group_trend = group_trend_doc["trend"]
    else:
        group_trend = {"trend": "STABLE", "current_rate": None, "forecast_rate": None}

    # Get most recent update time
    most_recent = max(
        (p.get("last_updated") for p in predictions if p.get("last_updated")),
        default=datetime.utcnow()
    )

    return jsonify({
        "generated_at": most_recent.isoformat() if isinstance(most_recent, datetime) else most_recent,
        "alerts": [serialize(p) for p in predictions],
        "summary": summary,
        "group_trend": group_trend,
        "source": "real_time_predictions"
    })


@predictions_bp.route("/<person_id>", methods=["GET"])
@jwt_required()
def get_person_prediction(person_id):
    """Get prediction for specific person"""
    db = current_app.db

    # Check if user has permission to view this person's data
    user_role = get_user_role()
    user_person_id = get_user_person_id()

    # Persons can only view their own predictions
    if user_role == "person" and user_person_id != person_id:
        return jsonify({"error": "You can only view your own predictions"}), 403

    # Teachers can only view persons in their department
    if user_role == "teacher" and not can_access_all_departments():
        user_dept = get_user_department()
        person = db.persons.find_one({"person_id": person_id})
        if not person or person.get("department") != user_dept:
            return jsonify({"error": "Access denied"}), 403

    pred = db.person_predictions.find_one({"person_id": person_id})

    if not pred:
        return jsonify({"error": "No prediction available for this person"}), 404

    return jsonify(serialize(pred))


@predictions_bp.route("/refresh", methods=["POST"])
@jwt_required()
def refresh_predictions():
    """
    Manually refresh predictions for all persons.
    This is the new "Run Analysis" - but it's much faster since it only
    updates predictions from existing data, doesn't retrain models.
    """
    db = current_app.db

    # Get ML service
    from ml_service import ml_service
    if not ml_service:
        return jsonify({"error": "ML service not initialized"}), 500

    # Get all persons
    persons = list(db.persons.find({}, {"person_id": 1}))
    person_ids = [p["person_id"] for p in persons]

    if not person_ids:
        return jsonify({"error": "No persons found in database"}), 400

    # Analyze all persons (this runs in foreground for manual refresh)
    results = ml_service.analyze_multiple_persons(person_ids)

    # Count results
    analyzed = sum(1 for r in results if r.get("alert_level"))
    insufficient = sum(1 for r in results if r.get("status") == "insufficient_data")
    errors = sum(1 for r in results if r.get("status") == "error")

    return jsonify({
        "message": "Predictions refreshed successfully",
        "total_persons": len(person_ids),
        "analyzed": analyzed,
        "insufficient_data": insufficient,
        "errors": errors
    })


@predictions_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_prediction_stats():
    """Get statistics about current predictions"""
    db = current_app.db

    total = db.person_predictions.count_documents({})

    if total == 0:
        return jsonify({"error": "No predictions available"}), 404

    stats = {
        "total_predictions": total,
        "by_level": {
            "critical": db.person_predictions.count_documents({"alert_level": "CRITICAL"}),
            "high": db.person_predictions.count_documents({"alert_level": "HIGH"}),
            "medium": db.person_predictions.count_documents({"alert_level": "MEDIUM"}),
            "low": db.person_predictions.count_documents({"alert_level": "LOW"}),
        },
        "last_updated": None
    }

    # Get most recent update
    most_recent = db.person_predictions.find_one(
        sort=[("last_updated", -1)],
        projection={"last_updated": 1}
    )

    if most_recent and "last_updated" in most_recent:
        stats["last_updated"] = most_recent["last_updated"].isoformat()

    return jsonify(stats)
