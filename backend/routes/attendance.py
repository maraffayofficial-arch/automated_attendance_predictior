from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
from middleware import admin_or_teacher_required, get_user_role, get_user_person_id
import csv
import io

attendance_bp = Blueprint("attendance", __name__)


def serialize(doc):
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


@attendance_bp.route("/", methods=["GET"])
@jwt_required()
def get_attendance():
    db = current_app.db
    person_id = request.args.get("person_id")
    limit = int(request.args.get("limit", 200))

    # Check permissions
    user_role = get_user_role()
    user_person_id = get_user_person_id()

    # If user is a person, they can only view their own attendance
    if user_role == "person":
        if not user_person_id:
            return jsonify({"error": "Access denied"}), 403
        person_id = user_person_id  # Override to ensure they only see their own data

    query = {}
    if person_id:
        query["person_id"] = person_id

    records = list(
        db.attendance_records.find(query).sort("date", -1).limit(limit)
    )
    return jsonify([serialize(r) for r in records])


@attendance_bp.route("/all", methods=["GET"])
@jwt_required()
def get_all_attendance():
    """Returns all records sorted by date — used by ML pipeline for retraining."""
    db = current_app.db
    records = list(db.attendance_records.find({}).sort([("person_id", 1), ("date", 1)]))
    return jsonify([serialize(r) for r in records])


@attendance_bp.route("/", methods=["POST"])
@admin_or_teacher_required
def add_attendance():
    db = current_app.db
    data = request.get_json()

    for field in ["person_id", "date", "attendance_binary"]:
        if field not in data:
            return jsonify({"error": f"'{field}' is required"}), 400

    if data["attendance_binary"] not in (0, 1):
        return jsonify({"error": "attendance_binary must be 0 or 1"}), 400

    if db.attendance_records.find_one({"person_id": data["person_id"], "date": data["date"]}):
        return jsonify({"error": "Record already exists for this person on this date"}), 409

    # Get current user for audit trail
    recorded_by = get_jwt_identity()

    record = {
        "person_id": data["person_id"],
        "date": data["date"],
        "attendance_binary": int(data["attendance_binary"]),
        "is_exam_period": int(data.get("is_exam_period", 0)),
        "created_at": datetime.utcnow(),
        "recorded_by": recorded_by,  # Audit trail
    }

    result = db.attendance_records.insert_one(record)
    record["_id"] = str(result.inserted_id)
    record["created_at"] = record["created_at"].isoformat()
    return jsonify(record), 201


@attendance_bp.route("/bulk", methods=["POST"])
@admin_or_teacher_required
def bulk_import():
    db = current_app.db

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    try:
        content = file.read().decode("utf-8")
    except UnicodeDecodeError:
        content = file.read().decode("latin-1")

    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)

    if not rows:
        return jsonify({"inserted": 0, "skipped": 0, "errors": ["CSV file is empty or has no data rows"]})

    errors = []
    valid_rows = []

    # Get current user for audit trail
    recorded_by = get_jwt_identity()

    for i, row in enumerate(rows, start=2):
        person_id = row.get("person_id", "").strip()
        date = row.get("date", "").strip()
        if not person_id or not date:
            errors.append(f"Row {i}: missing person_id or date")
            continue
        try:
            valid_rows.append({
                "person_id": person_id,
                "date": date,
                "attendance_binary": int(float(row.get("attendance_binary", 0))),
                "is_exam_period": int(float(row.get("is_exam_period", 0))),
                "created_at": datetime.utcnow(),
                "recorded_by": recorded_by,  # Audit trail
            })
        except (ValueError, TypeError) as e:
            errors.append(f"Row {i}: {str(e)}")

    if not valid_rows:
        return jsonify({"inserted": 0, "skipped": 0, "errors": errors})

    # Fetch all existing (person_id, date) pairs in one query
    keys = [{"person_id": r["person_id"], "date": r["date"]} for r in valid_rows]
    existing = set(
        (doc["person_id"], doc["date"])
        for doc in db.attendance_records.find(
            {"$or": keys}, {"person_id": 1, "date": 1, "_id": 0}
        )
    )

    to_insert = [r for r in valid_rows if (r["person_id"], r["date"]) not in existing]
    skipped = len(valid_rows) - len(to_insert)

    inserted = 0
    affected_persons = set()

    if to_insert:
        try:
            result = db.attendance_records.insert_many(to_insert, ordered=False)
            inserted = len(result.inserted_ids)

            # Track affected persons for ML analysis
            affected_persons = set(r["person_id"] for r in to_insert)
        except Exception as e:
            errors.append(f"Bulk insert error: {str(e)}")

    # NEW: Automatically analyze affected persons in background
    if affected_persons:
        from ml_service import ml_service
        if ml_service:
            from threading import Thread
            def analyze_async():
                try:
                    ml_service.analyze_multiple_persons(list(affected_persons))
                    print(f"✓ Auto-analyzed {len(affected_persons)} persons after bulk import")
                except Exception as e:
                    print(f"✗ Auto-analysis failed: {e}")

            Thread(target=analyze_async, daemon=True).start()

    return jsonify({
        "inserted": inserted,
        "skipped": skipped,
        "analyzing": len(affected_persons),
        "errors": errors
    })


@attendance_bp.route("/<record_id>", methods=["DELETE"])
@admin_or_teacher_required
def delete_record(record_id):
    db = current_app.db
    try:
        result = db.attendance_records.delete_one({"_id": ObjectId(record_id)})
    except Exception:
        return jsonify({"error": "Invalid record ID"}), 400

    if result.deleted_count == 0:
        return jsonify({"error": "Record not found"}), 404

    return jsonify({"message": "Deleted successfully"})


@attendance_bp.route("/daily", methods=["POST"])
@admin_or_teacher_required
def record_daily_attendance():
    """Record attendance for multiple persons on a specific date."""
    db = current_app.db
    data = request.get_json()

    date = data.get("date")
    records = data.get("records", [])
    is_exam_period = int(data.get("is_exam_period", 0))

    if not date:
        return jsonify({"error": "Date is required"}), 400

    if not records:
        return jsonify({"error": "No attendance records provided"}), 400

    inserted = 0
    updated = 0
    errors = []
    affected_persons = set()

    # Get current user for audit trail
    recorded_by = get_jwt_identity()

    for rec in records:
        person_id = rec.get("person_id")
        attendance_binary = rec.get("attendance_binary")

        if not person_id or attendance_binary not in (0, 1):
            errors.append(f"Invalid record for person_id: {person_id}")
            continue

        # Track affected persons for ML analysis
        affected_persons.add(person_id)

        # Check if record exists
        existing = db.attendance_records.find_one({
            "person_id": person_id,
            "date": date
        })

        if existing:
            # Update existing record
            db.attendance_records.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "attendance_binary": int(attendance_binary),
                    "is_exam_period": is_exam_period,
                    "updated_at": datetime.utcnow(),
                    "updated_by": recorded_by,  # Audit trail
                }}
            )
            updated += 1
        else:
            # Insert new record
            db.attendance_records.insert_one({
                "person_id": person_id,
                "date": date,
                "attendance_binary": int(attendance_binary),
                "is_exam_period": is_exam_period,
                "created_at": datetime.utcnow(),
                "recorded_by": recorded_by,  # Audit trail
            })
            inserted += 1

    # NEW: Automatically analyze affected persons in background
    if affected_persons:
        from ml_service import ml_service
        if ml_service:
            from threading import Thread
            def analyze_async():
                try:
                    ml_service.analyze_multiple_persons(list(affected_persons))
                    print(f"[OK] Auto-analyzed {len(affected_persons)} persons after attendance update")
                except Exception as e:
                    print(f"[ERROR] Auto-analysis failed: {e}")

            Thread(target=analyze_async, daemon=True).start()

    return jsonify({
        "message": "Attendance recorded successfully",
        "inserted": inserted,
        "updated": updated,
        "analyzing": len(affected_persons),
        "errors": errors
    }), 200


@attendance_bp.route("/date/<date>", methods=["GET"])
@jwt_required()
def get_attendance_by_date(date):
    """Get all attendance records for a specific date."""
    db = current_app.db
    records = list(db.attendance_records.find({"date": date}))
    return jsonify([serialize(r) for r in records])


@attendance_bp.route("/stats/today", methods=["GET"])
@jwt_required()
def get_today_stats():
    """Get today's attendance statistics."""
    db = current_app.db
    today = datetime.utcnow().strftime("%Y-%m-%d")

    records = list(db.attendance_records.find({"date": today}))
    total_persons = db.persons.count_documents({})

    present = sum(1 for r in records if r["attendance_binary"] == 1)
    absent = sum(1 for r in records if r["attendance_binary"] == 0)
    not_marked = total_persons - len(records)

    attendance_rate = (present / total_persons * 100) if total_persons > 0 else 0

    return jsonify({
        "date": today,
        "total_persons": total_persons,
        "present": present,
        "absent": absent,
        "not_marked": not_marked,
        "attendance_rate": round(attendance_rate, 2),
        "is_complete": not_marked == 0
    })


@attendance_bp.route("/stats/weekly", methods=["GET"])
@jwt_required()
def get_weekly_stats():
    """Get weekly attendance statistics."""
    db = current_app.db
    from datetime import timedelta

    today = datetime.utcnow()
    week_ago = today - timedelta(days=7)

    records = list(db.attendance_records.find({
        "date": {"$gte": week_ago.strftime("%Y-%m-%d")}
    }))

    # Group by date
    daily_stats = {}
    for rec in records:
        date = rec["date"]
        if date not in daily_stats:
            daily_stats[date] = {"present": 0, "absent": 0, "total": 0}

        daily_stats[date]["total"] += 1
        if rec["attendance_binary"] == 1:
            daily_stats[date]["present"] += 1
        else:
            daily_stats[date]["absent"] += 1

    # Calculate rates
    result = []
    for date in sorted(daily_stats.keys()):
        stats = daily_stats[date]
        rate = (stats["present"] / stats["total"] * 100) if stats["total"] > 0 else 0
        result.append({
            "date": date,
            "present": stats["present"],
            "absent": stats["absent"],
            "total": stats["total"],
            "attendance_rate": round(rate, 2)
        })

    return jsonify(result)


@attendance_bp.route("/self", methods=["POST"])
@jwt_required()
def mark_self_attendance():
    """Allow persons to mark their own attendance for today only."""
    db = current_app.db

    # Get person_id from JWT token
    person_id = get_user_person_id()

    if not person_id:
        return jsonify({"error": "Only person accounts can mark self-attendance"}), 403

    data = request.get_json()
    attendance_binary = data.get("attendance_binary")

    if attendance_binary not in (0, 1):
        return jsonify({"error": "attendance_binary must be 0 or 1"}), 400

    # Only allow marking attendance for today
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Check if already marked today
    existing = db.attendance_records.find_one({
        "person_id": person_id,
        "date": today
    })

    recorded_by = get_jwt_identity()

    if existing:
        # Update existing record
        db.attendance_records.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "attendance_binary": int(attendance_binary),
                "updated_at": datetime.utcnow(),
                "updated_by": recorded_by,
            }}
        )
        message = "Attendance updated successfully"
    else:
        # Insert new record
        record = {
            "person_id": person_id,
            "date": today,
            "attendance_binary": int(attendance_binary),
            "is_exam_period": 0,
            "created_at": datetime.utcnow(),
            "recorded_by": recorded_by,
        }
        db.attendance_records.insert_one(record)
        message = "Attendance marked successfully"

    # Trigger ML analysis in background
    from ml_service import ml_service
    if ml_service:
        from threading import Thread
        def analyze_async():
            try:
                ml_service.analyze_person(person_id)
                print(f"[OK] Auto-analyzed {person_id} after self-attendance")
            except Exception as e:
                print(f"[ERROR] Auto-analysis failed: {e}")

        Thread(target=analyze_async, daemon=True).start()

    return jsonify({
        "message": message,
        "person_id": person_id,
        "date": today,
        "attendance_binary": attendance_binary
    }), 200


@attendance_bp.route("/self/today", methods=["GET"])
@jwt_required()
def get_self_attendance_today():
    """Get current user's attendance status for today."""
    db = current_app.db

    person_id = get_user_person_id()

    if not person_id:
        return jsonify({"error": "Only person accounts can access this endpoint"}), 403

    today = datetime.utcnow().strftime("%Y-%m-%d")

    record = db.attendance_records.find_one({
        "person_id": person_id,
        "date": today
    })

    if record:
        return jsonify({
            "marked": True,
            "date": today,
            "attendance_binary": record["attendance_binary"],
            "created_at": record["created_at"].isoformat() if isinstance(record.get("created_at"), datetime) else None
        })
    else:
        return jsonify({
            "marked": False,
            "date": today
        })

