# 🎓 Attendance Predictor - AI-Powered Attendance Intelligence System

An intelligent attendance management system that uses machine learning to predict attendance patterns, detect anomalies, and provide early intervention recommendations.

## 🌟 Features

### For Students/Employees (Person Role)
- ✅ Self-service attendance marking
- 📊 View personal attendance history
- 🎯 See risk level and predictions
- 📈 Track attendance trends

### For Teachers
- 📝 Record attendance for their department
- 👥 View department-specific predictions
- 🔍 Monitor student/employee attendance patterns
- 📋 Manage persons in their department

### For Admins
- 🌐 Full system access across all departments
- 📊 Dashboard with comprehensive analytics
- 👤 User management
- 📁 Bulk CSV import/export

### ML-Powered Intelligence
- 🤖 **3 ML Models Working Together:**
  - **XGBoost** - Predicts next 7 days absence probability
  - **Isolation Forest** - Detects attendance anomalies
  - **Prophet** - Forecasts group attendance trends
- 🚨 Real-time risk scoring (CRITICAL, HIGH, MEDIUM, LOW)
- 💡 Personalized intervention recommendations
- 🔄 Automatic analysis on attendance recording

## 🏗️ Architecture

```
Frontend (React + Vite)
    ↓
Backend (Flask REST API)
    ↓
MongoDB Atlas (Database)
    ↓
ML Models (XGBoost, Isolation Forest, Prophet)
```

## 🚀 Tech Stack

### Backend
- **Framework:** Flask 3.1.3
- **Database:** MongoDB (PyMongo)
- **Authentication:** JWT (Flask-JWT-Extended)
- **ML Libraries:** scikit-learn, XGBoost, Prophet
- **Server:** Gunicorn

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite
- **Routing:** React Router
- **HTTP Client:** Axios
- **Styling:** Tailwind CSS
- **Icons:** Lucide React

## 📦 Project Structure

```
attendance_predictor/
├── backend/
│   ├── app.py                 # Flask application
│   ├── config.py              # Configuration
│   ├── ml_service.py          # ML analysis service
│   ├── middleware.py          # Auth middleware
│   ├── routes/
│   │   ├── auth.py           # Authentication routes
│   │   ├── persons.py        # Person management
│   │   ├── attendance.py     # Attendance recording
│   │   ├── predictions.py    # ML predictions
│   │   └── alerts.py         # Legacy alerts
│   ├── attendance_predictor/
│   │   └── models/           # Trained ML models
│   ├── requirements.txt      # Python dependencies
│   ├── Procfile             # Railway deployment
│   └── railway.json         # Railway config
├── frontend/
│   ├── src/
│   │   ├── pages/           # React pages
│   │   ├── components/      # Reusable components
│   │   ├── context/         # Auth context
│   │   └── api/             # API client
│   ├── package.json
│   └── vercel.json          # Vercel config
└── DEPLOYMENT.md            # Deployment guide
```

## 🔐 User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access to all departments and features |
| **Teacher** | Department-specific access, can record attendance |
| **Viewer** | Read-only access to predictions and data |
| **Person** | Self-service attendance marking only |

## 🎯 ML Models

### 1. XGBoost Classifier
- **Purpose:** Predicts absence probability for next 7 days
- **Features:** Rolling averages, streaks, day of week, exam periods
- **Output:** Daily forecasts + predicted absences count

### 2. Isolation Forest
- **Purpose:** Detects anomalous attendance patterns
- **Detects:** Sudden drops, exam absences, erratic patterns, prolonged absences
- **Output:** Anomaly score + anomaly types

### 3. Prophet
- **Purpose:** Group-level attendance trend forecasting
- **Output:** IMPROVING, DECLINING, or STABLE trend
- **Cached:** Updated once per day for efficiency

## 📊 Key Metrics

- **Combined Risk Score:** Weighted average of all 3 models
- **Alert Levels:** CRITICAL (>80%), HIGH (60-80%), MEDIUM (40-60%), LOW (<40%)
- **Minimum Data:** 7 days of attendance required for predictions

## 🌐 Deployment

Deployed on:
- **Backend:** Railway.app
- **Frontend:** Vercel
- **Database:** MongoDB Atlas

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## 🔧 Local Development

### Prerequisites
- Python 3.9+
- Node.js 18+
- MongoDB (local or Atlas)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your MongoDB URI and JWT secret
python app.py
```

Backend runs on: http://localhost:5000

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on: http://localhost:5173

## 📝 Environment Variables

### Backend (.env)
```
MONGO_URI=mongodb://localhost:27017/attendance_db
JWT_SECRET_KEY=your-secret-key
FLASK_PORT=5000
FRONTEND_URL=http://localhost:5173
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:5000/api
```

## 🧪 Testing

### Test Backend Health
```bash
curl http://localhost:5000/api/health
```

### Test ML Models
```bash
cd backend
python -c "from ml_service import MLService; print('Models loaded successfully')"
```

## 📈 Usage Flow

1. **Admin** adds persons to the system
2. **Person** registers with their person_id
3. **Person** logs in and marks attendance daily
4. **ML models** automatically analyze and predict
5. **Teachers/Admins** view predictions and take action

## 🤝 Contributing

This project was developed as part of KHSIP-2026-MG-0002.

## 📄 License

All rights reserved.

## 👨‍💻 Author

Developed with ❤️ using Claude Code

---

**Live Demo:** [Your Vercel URL]  
**API Docs:** [Your Railway URL]/api/health
