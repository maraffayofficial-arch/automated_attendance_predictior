from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from datetime import datetime
from middleware import can_access_all_departments, get_user_department, admin_or_teacher_required
import csv
import io

persons_bp = Blueprint("persons", __name__)


def serialize(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@persons_bp.route("/", methods=["GET"])
@jwt_required()
def get_persons():
    db = current_app.db
    query = {}

    # Department filtering for teachers
    if not can_access_all_departments():
        user_dept = get_user_department()
        if user_dept:
            query["department"] = user_dept
        else:
            # Teacher with no department sees nothing
            return jsonify([])

    person_type = request.args.get("type")
    if person_type and person_type != "all":
        query["type"] = person_type

    search = request.args.get("search", "").strip()
    if search:
        search_conditions = [
            {"person_id": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
            {"department": {"$regex": search, "$options": "i"}},
        ]
        if "$or" in query:
            query["$and"] = [{"$or": query["$or"]}, {"$or": search_conditions}]
            del query["$or"]
        else:
            query["$or"] = search_conditions

    persons = list(db.persons.find(query).sort("person_id", 1))
    return jsonify([serialize(p) for p in persons])


@persons_bp.route("/", methods=["POST"])
@admin_or_teacher_required
def create_person():
    db = current_app.db
    data = request.get_json()

    for field in ["person_id", "name", "type"]:
        if not data.get(field, "").strip():
            return jsonify({"error": f"'{field}' is required"}), 400

    if data["type"] not in ("student", "employee"):
        return jsonify({"error": "type must be 'student' or 'employee'"}), 400

    if db.persons.find_one({"person_id": data["person_id"]}):
        return jsonify({"error": "person_id already exists"}), 409

    person = {
        "person_id": data["person_id"].strip(),
        "name": data["name"].strip(),
        "type": data["type"],
        "department": data.get("department", "").strip(),
        "email": data.get("email", "").strip(),
        "created_at": datetime.utcnow(),
    }

    result = db.persons.insert_one(person)
    person["_id"] = str(result.inserted_id)
    person["created_at"] = person["created_at"].isoformat()
    return jsonify(person), 201


@persons_bp.route("/<person_id>", methods=["GET"])
@jwt_required()
def get_person(person_id):
    db = current_app.db
    person = db.persons.find_one({"person_id": person_id})
    if not person:
        return jsonify({"error": "Person not found"}), 404
    return jsonify(serialize(person))


@persons_bp.route("/<person_id>", methods=["PUT"])
@admin_or_teacher_required
def update_person(person_id):
    db = current_app.db
    data = request.get_json()

    allowed = ["name", "type", "department", "email"]
    update = {k: data[k] for k in allowed if k in data}

    if "type" in update and update["type"] not in ("student", "employee"):
        return jsonify({"error": "type must be 'student' or 'employee'"}), 400

    result = db.persons.update_one({"person_id": person_id}, {"$set": update})
    if result.matched_count == 0:
        return jsonify({"error": "Person not found"}), 404

    return jsonify({"message": "Updated successfully"})


@persons_bp.route("/<person_id>", methods=["DELETE"])
@admin_or_teacher_required
def delete_person(person_id):
    db = current_app.db
    result = db.persons.delete_one({"person_id": person_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Person not found"}), 404
    return jsonify({"message": "Deleted successfully"})


@persons_bp.route("/import", methods=["POST"])
@admin_or_teacher_required
def import_persons():
    db = current_app.db

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    content = file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    inserted, skipped, errors = 0, 0, []

    for i, row in enumerate(reader, start=2):
        person_id = row.get("person_id", "").strip()
        name = row.get("name", "").strip()
        person_type = row.get("type", "employee").strip()

        if not person_id or not name:
            errors.append(f"Row {i}: missing person_id or name")
            continue

        if db.persons.find_one({"person_id": person_id}):
            skipped += 1
            continue

        db.persons.insert_one({
            "person_id": person_id,
            "name": name,
            "type": person_type if person_type in ("student", "employee") else "employee",
            "department": row.get("department", "").strip(),
            "email": row.get("email", "").strip(),
            "created_at": datetime.utcnow(),
        })
        inserted += 1

    return jsonify({"inserted": inserted, "skipped": skipped, "errors": errors})
