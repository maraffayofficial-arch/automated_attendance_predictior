# Daily Attendance Recording Feature

## Overview
The attendance predictor app now includes a complete daily attendance recording system. Admins can mark daily attendance for all persons, view attendance history, and export reports - while still maintaining all the ML prediction and anomaly detection features.

## New Features Added

### 1. Daily Attendance Recording (`/attendance/daily`)
- **Bulk attendance entry** - Mark all persons present/absent at once
- **Individual marking** - Toggle attendance for each person
- **Date selection** - Record attendance for any past date
- **Exam period flag** - Mark if the day is during exam period
- **Real-time statistics** - See present/absent counts as you mark
- **Search and filter** - Find persons quickly, filter by marked/unmarked status
- **Auto-save** - Updates existing records if attendance already recorded

### 2. Attendance History (`/attendance/history`)
- **Weekly trends** - View last 7 days of attendance data
- **Attendance rate tracking** - See daily attendance percentages
- **Individual history** - View attendance records for specific persons
- **Export to CSV** - Download attendance reports
- **Visual indicators** - Color-coded attendance rates (green/yellow/red)
- **Trend arrows** - See if attendance is improving or declining

### 3. Today's Statistics Dashboard
- Total persons count
- Present/absent counts
- Not marked count
- Real-time attendance rate
- Completion status

## New Backend Endpoints

### POST `/api/attendance/daily`
Record attendance for multiple persons on a specific date.

**Request:**
```json
{
  "date": "2026-04-29",
  "records": [
    {"person_id": "EMP-001", "attendance_binary": 1},
    {"person_id": "EMP-002", "attendance_binary": 0}
  ],
  "is_exam_period": 0
}
```

**Response:**
```json
{
  "message": "Attendance recorded successfully",
  "inserted": 5,
  "updated": 3,
  "errors": []
}
```

### GET `/api/attendance/date/{date}`
Get all attendance records for a specific date.

**Response:**
```json
[
  {
    "_id": "...",
    "person_id": "EMP-001",
    "date": "2026-04-29",
    "attendance_binary": 1,
    "is_exam_period": 0,
    "created_at": "2026-04-29T08:00:00"
  }
]
```

### GET `/api/attendance/stats/today`
Get today's attendance statistics.

**Response:**
```json
{
  "date": "2026-04-29",
  "total_persons": 50,
  "present": 42,
  "absent": 5,
  "not_marked": 3,
  "attendance_rate": 89.36,
  "is_complete": false
}
```

### GET `/api/attendance/stats/weekly`
Get weekly attendance statistics (last 7 days).

**Response:**
```json
[
  {
    "date": "2026-04-29",
    "present": 42,
    "absent": 5,
    "total": 47,
    "attendance_rate": 89.36
  },
  {
    "date": "2026-04-28",
    "present": 45,
    "absent": 3,
    "total": 48,
    "attendance_rate": 93.75
  }
]
```

## Frontend Pages

### Daily Attendance Page (`/attendance/daily`)
**Features:**
- Date picker (defaults to today)
- Search bar to find persons
- Filter dropdown (All/Marked/Unmarked/Present/Absent)
- Exam period checkbox
- Mark All Present/Absent buttons
- Individual Present/Absent buttons for each person
- Real-time statistics showing marked count and attendance rate
- Save button to submit attendance

**Navigation:** Click "Daily Attendance" in the sidebar

### Attendance History Page (`/attendance/history`)
**Features:**
- Summary cards showing average rate, total present/absent
- Weekly stats table with trend indicators
- Export to CSV button
- Individual person history viewer
- Color-coded attendance rates
- Date formatting with weekday names

**Navigation:** Click "Attendance History" in the sidebar

## How to Use

### Recording Daily Attendance

1. **Start the backend:**
   ```bash
   cd backend
   python app.py
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Login:**
   - Username: `admin`
   - Password: `admin123`

4. **Navigate to Daily Attendance:**
   - Click "Daily Attendance" in the sidebar
   - Select today's date (or any past date)
   - Mark attendance for each person (or use Mark All buttons)
   - Check "Exam Period" if applicable
   - Click "Save Attendance"

5. **View History:**
   - Click "Attendance History" in the sidebar
   - See weekly trends and statistics
   - Select a person to view their individual history
   - Export data to CSV if needed

### Testing the New Endpoints

Run the test script:
```bash
cd /c/Users/HP/Downloads/attendance_predictor_
python test_new_endpoints.py
```

This will test all new endpoints and verify they're working correctly.

## Workflow

### Daily Workflow
1. **Morning:** Admin opens Daily Attendance page
2. **Mark Attendance:** Records who is present/absent for the day
3. **Save:** Submits the attendance data
4. **ML Pipeline:** Runs automatically (scheduled) to generate predictions
5. **Dashboard:** Admin views predictions and anomalies

### Weekly Workflow
1. **Review History:** Check attendance trends over the week
2. **Export Reports:** Download CSV for record-keeping
3. **ML Retraining:** Adaptive learning script retrains models with new data

## Integration with ML Pipeline

The daily attendance recording integrates seamlessly with the existing ML pipeline:

1. **Data Collection:** Attendance is recorded via the new UI
2. **Storage:** Records stored in MongoDB with proper schema
3. **ML Input:** The ML pipeline reads from the same database
4. **Predictions:** Models generate forecasts and anomaly alerts
5. **Dashboard:** Admin sees both actual attendance and predictions

## Database Schema

The attendance records follow the same 4-column schema required by the ML pipeline:

| Column | Type | Description |
|--------|------|-------------|
| person_id | string | Unique identifier |
| date | date | Attendance date (YYYY-MM-DD) |
| attendance_binary | integer | 1 = present, 0 = absent |
| is_exam_period | integer | 1 = exam period, 0 = normal |

## User Roles

Currently, all features are available to the `admin` role. The authentication system supports role-based access:

- **admin:** Full access (record attendance, view predictions, manage persons)
- **viewer:** Read-only access (view dashboards and reports)
- **attendance_taker:** (Future) Can only record attendance, no predictions

To add an attendance_taker role in the future, update the auth system to restrict access to prediction endpoints.

## Export Format

CSV exports include:
- Date
- Present count
- Absent count
- Total count
- Attendance rate (%)

Filename format: `attendance_history_YYYY-MM-DD.csv`

## Notes

- Attendance can be recorded for past dates (useful for corrections)
- Updating attendance for an already-recorded date will update the existing records
- The system prevents duplicate records (person + date combination is unique)
- All times are stored in UTC
- The frontend displays dates in the user's local timezone

## Future Enhancements

Potential additions:
- Bulk import from Excel/CSV
- Attendance notifications (SMS/Email for absences)
- Mobile app for quick attendance marking
- QR code scanning for automated attendance
- Biometric integration
- Late arrival tracking (not just present/absent)
- Leave management integration
- Parent/guardian notifications
