from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
import bcrypt

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    db = current_app.db
    data = request.get_json()

    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "viewer")
    department = data.get("department", "").strip()
    person_id = data.get("person_id", "").strip()  # NEW: Link user to person

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if db.users.find_one({"username": username}):
        return jsonify({"error": "Username already exists"}), 409

    # Validate role
    if role not in ["admin", "teacher", "viewer", "person"]:
        return jsonify({"error": "Role must be admin, teacher, viewer, or person"}), 400

    # Teachers must have a department
    if role == "teacher" and not department:
        return jsonify({"error": "Teachers must have a department assigned"}), 400

    # Persons must have a person_id and it must exist in persons collection
    if role == "person":
        if not person_id:
            return jsonify({"error": "person_id is required for person role"}), 400

        person = db.persons.find_one({"person_id": person_id})
        if not person:
            return jsonify({"error": "person_id does not exist in the system"}), 404

        # Check if person_id is already linked to another user
        if db.users.find_one({"person_id": person_id}):
            return jsonify({"error": "This person_id is already registered"}), 409

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    user = {
        "username": username,
        "password_hash": password_hash,
        "role": role,
        "department": department if department else None,
        "person_id": person_id if person_id else None,
        "created_at": datetime.utcnow(),
    }

    result = db.users.insert_one(user)
    return jsonify({"message": "User created", "id": str(result.inserted_id)}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    db = current_app.db
    data = request.get_json()

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = db.users.find_one({"username": username})

    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"]):
        return jsonify({"error": "Invalid username or password"}), 401

    token = create_access_token(
        identity=username,
        additional_claims={
            "role": user["role"],
            "department": user.get("department"),
            "person_id": user.get("person_id")
        }
    )

    return jsonify({
        "token": token,
        "username": username,
        "role": user["role"],
        "department": user.get("department"),
        "person_id": user.get("person_id")
    })


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    username = get_jwt_identity()
    claims = get_jwt()
    return jsonify({
        "username": username,
        "role": claims.get("role"),
        "department": claims.get("department"),
        "person_id": claims.get("person_id")
    })
