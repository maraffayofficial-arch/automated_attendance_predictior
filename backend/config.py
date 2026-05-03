import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-this")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

ML_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "attendance_predictor")
)
