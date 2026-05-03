from flask import Flask, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import timedelta
from config import MONGO_URI, JWT_SECRET_KEY, FLASK_PORT
import os

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)  # Tokens expire after 24 hours
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# CORS configuration for production
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
CORS(app, origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:5175"], supports_credentials=True)
jwt = JWTManager(app)

client = MongoClient(MONGO_URI)
db = client.get_database()
app.db = db

# Create indexes on startup
db.persons.create_index([("person_id", ASCENDING)], unique=True)
db.attendance_records.create_index([("person_id", ASCENDING), ("date", ASCENDING)], unique=True)
db.alert_runs.create_index([("generated_at", DESCENDING)])
db.users.create_index([("username", ASCENDING)], unique=True)
db.person_predictions.create_index([("person_id", ASCENDING)], unique=True)
db.person_predictions.create_index([("alert_level_order", ASCENDING)])

# Initialize ML Service
print("\n" + "=" * 60)
print("  INITIALIZING ML SERVICE")
print("=" * 60)
try:
    import ml_service as ml_module
    ml_module.ml_service = ml_module.MLService(db)
    print("[OK] ML Service initialized successfully")
    print("  Real-time predictions enabled")
except Exception as e:
    print(f"[ERROR] ML Service failed to initialize: {e}")
    print("  Predictions will not be available until models are trained")
print("=" * 60 + "\n")

from routes.auth import auth_bp
from routes.persons import persons_bp
from routes.attendance import attendance_bp
from routes.alerts import alerts_bp
from routes.predictions import predictions_bp

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(persons_bp, url_prefix="/api/persons")
app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
app.register_blueprint(alerts_bp, url_prefix="/api/alerts")
app.register_blueprint(predictions_bp, url_prefix="/api/predictions")

# Apply rate limiting to specific endpoints
limiter.limit("5 per minute")(auth_bp.view_functions['login'])
limiter.limit("10 per hour")(auth_bp.view_functions['register'])

@app.route("/api/health")
def health():
    return {"status": "ok", "db": db.name}

@app.route("/api/health/ml")
def ml_health():
    """Check if ML models are loaded and working"""
    try:
        from ml_service import ml_service
        if ml_service and ml_service.models:
            models_status = {
                "xgboost": "loaded" if ml_service.models.get("xgboost") else "missing",
                "isolation_forest": "loaded" if ml_service.models.get("isolation_forest") else "missing",
                "prophet": "loaded" if ml_service.models.get("prophet") else "missing"
            }
            all_loaded = all(status == "loaded" for status in models_status.values())
            return {
                "status": "ok" if all_loaded else "partial",
                "models": models_status,
                "message": "All models loaded" if all_loaded else "Some models missing"
            }
        return {"status": "error", "message": "ML service not initialized"}, 500
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", FLASK_PORT))
    app.run(host="0.0.0.0", port=port, debug=False)
