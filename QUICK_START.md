# Quick Start Guide - Daily Attendance Feature

## Prerequisites
- Python 3.13+ installed
- Node.js installed
- MongoDB connection (already configured in backend/.env)

## Step 1: Start the Backend

```bash
cd /c/Users/HP/Downloads/attendance_predictor_/backend
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
```

## Step 2: Start the Frontend

Open a new terminal:

```bash
cd /c/Users/HP/Downloads/attendance_predictor_/frontend
npm run dev
```

You should see:
```
Local: http://localhost:5173
```

## Step 3: Login

1. Open browser to `http://localhost:5173`
2. Login with:
   - **Username:** `admin`
   - **Password:** `admin123`

## Step 4: Record Today's Attendance

1. Click **"Daily Attendance"** in the sidebar
2. Today's date (2026-04-29) should be pre-selected
3. You'll see all persons listed
4. For each person, click either:
   - **Present** (green button)
   - **Absent** (red button)
5. Or use quick actions:
   - **Mark All Present** - marks everyone present
   - **Mark All Absent** - marks everyone absent
6. Check **"Exam Period"** if today is during exams
7. Click **"Save Attendance"** button

## Step 5: View Statistics

### Today's Stats (shown at top of Daily Attendance page):
- Total Persons
- Present Count
- Absent Count
- Not Marked Count
- Attendance Rate %

### Weekly History:
1. Click **"Attendance History"** in the sidebar
2. See last 7 days of attendance data
3. View trends and patterns
4. Export to CSV if needed

### Individual History:
1. On Attendance History page
2. Select a person from dropdown
3. See their attendance records for last 30 days

## Step 6: View Predictions (Existing Feature)

1. Click **"Dashboard"** in the sidebar
2. See ML predictions and anomaly alerts
3. View persons at risk of absence
4. Check group attendance trends

## Navigation Overview

```
├── Dashboard (Predictions & Anomalies)
├── Daily Attendance (NEW - Record attendance)
├── Attendance History (NEW - View trends)
└── Persons (Manage persons)
```

## Common Tasks

### Record Attendance for Yesterday
1. Go to Daily Attendance
2. Change date picker to yesterday
3. Mark attendance
4. Save

### Correct a Mistake
1. Go to Daily Attendance
2. Select the date
3. Change the attendance status
4. Save (will update existing record)

### Export Attendance Report
1. Go to Attendance History
2. Click "Export CSV" button
3. File downloads automatically

### Add New Person
1. Go to Persons page
2. Click "Add Person"
3. Fill in details
4. Save
5. They'll appear in Daily Attendance list

## Troubleshooting

### Backend won't start
- Check if MongoDB connection is working
- Verify .env file exists in backend folder
- Check if port 5000 is available

### Frontend won't start
- Run `npm install` in frontend folder first
- Check if port 5173 is available

### Can't login
- Make sure backend is running
- Check browser console for errors
- Try clearing browser cache/localStorage

### Attendance not saving
- Check browser console for errors
- Verify you're logged in (token valid)
- Check backend terminal for error messages

## Testing

Run the test script to verify all endpoints:

```bash
cd /c/Users/HP/Downloads/attendance_predictor_
python test_new_endpoints.py
```

Expected output:
```
✓ Login successful
✓ Today's stats: {...}
✓ Weekly stats: 7 days of data
✓ Daily attendance recorded
✓ Found 3 records for 2026-04-29
✅ All tests completed!
```

## What's Next?

After recording attendance daily:
1. The ML pipeline will use this data for predictions
2. Run `python alert_system.py` to generate new predictions
3. View updated predictions on Dashboard
4. Check for anomalies and high-risk persons

## Support

For issues or questions:
- Check DAILY_ATTENDANCE_FEATURE.md for detailed documentation
- Review backend logs in terminal
- Check browser console for frontend errors
