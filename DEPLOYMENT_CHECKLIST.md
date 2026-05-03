# 🚀 Pre-Deployment Checklist

**Project:** Attendance Predictor  
**Date:** May 3, 2026  
**Status:** Ready for Deployment

---

## ✅ Code Readiness

### Backend
- [x] All Python dependencies in requirements.txt
- [x] Environment variables documented (.env.example)
- [x] JWT token expiration configured (24 hours)
- [x] Rate limiting enabled
- [x] CORS configured for production
- [x] Health check endpoints working
- [x] ML models loading correctly
- [x] Logging implemented
- [x] Error handling added
- [x] Procfile created for Railway
- [x] railway.json configured

### Frontend
- [x] API URL configurable via environment variable
- [x] All pages working
- [x] Role-based navigation implemented
- [x] Error messages user-friendly
- [x] Responsive design tested
- [x] vercel.json configured
- [x] Build command verified

### Database
- [x] MongoDB Atlas account ready
- [x] Connection string available
- [x] Collections and indexes defined
- [x] Sample data tested

### ML Models
- [x] All 3 models present (XGBoost, Isolation Forest, Prophet)
- [x] Models loading without errors
- [x] Version compatibility fixed (scikit-learn==1.6.1)
- [x] Total size: 1.4 MB (within limits)

---

## 📋 Pre-Deployment Tasks

### 1. Local Testing
- [ ] Backend runs without errors: `cd backend && python app.py`
- [ ] Frontend builds successfully: `cd frontend && npm run build`
- [ ] Can register new user
- [ ] Can login successfully
- [ ] Can mark attendance
- [ ] ML predictions working
- [ ] All 4 roles tested (Admin, Teacher, Viewer, Person)

### 2. Environment Variables Ready
- [ ] MongoDB Atlas connection string
- [ ] JWT secret key generated
- [ ] Frontend URL for CORS
- [ ] Backend URL for frontend

### 3. Accounts Created
- [ ] GitHub account
- [ ] Railway account (https://railway.app)
- [ ] Vercel account (https://vercel.com)
- [ ] MongoDB Atlas account (already done ✓)

### 4. Git Repository
- [ ] Code pushed to GitHub
- [ ] .gitignore configured
- [ ] .env files NOT committed
- [ ] README.md updated

---

## 🚂 Railway Deployment Checklist

### Setup
- [ ] New project created on Railway
- [ ] GitHub repository connected
- [ ] Root directory set to: `backend`
- [ ] Build command: `pip install -r requirements.txt`
- [ ] Start command: `gunicorn app:app`

### Environment Variables
- [ ] `MONGO_URI` = Your MongoDB Atlas connection string
- [ ] `JWT_SECRET_KEY` = Random secret (use: `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] `FRONTEND_URL` = Your Vercel URL (add after Vercel deployment)

### Verification
- [ ] Deployment successful (green checkmark)
- [ ] Domain generated
- [ ] Health check works: `https://your-app.railway.app/api/health`
- [ ] ML health check works: `https://your-app.railway.app/api/health/ml`
- [ ] Logs show models loaded successfully

---

## 🌐 Vercel Deployment Checklist

### Setup
- [ ] New project created on Vercel
- [ ] GitHub repository imported
- [ ] Framework preset: Vite
- [ ] Root directory set to: `frontend`
- [ ] Build command: `npm run build`
- [ ] Output directory: `dist`

### Environment Variables
- [ ] `VITE_API_URL` = Your Railway backend URL + `/api`
  - Example: `https://attendance-backend.railway.app/api`

### Verification
- [ ] Deployment successful
- [ ] Domain generated
- [ ] Can access login page
- [ ] Can register and login
- [ ] API calls working (check browser console)

---

## 🔄 Post-Deployment Tasks

### Update CORS
- [ ] Go back to Railway
- [ ] Update `FRONTEND_URL` environment variable with Vercel URL
- [ ] Redeploy backend

### Final Testing
- [ ] Register a new person account
- [ ] Login successfully
- [ ] Mark attendance
- [ ] Check predictions appear
- [ ] Test all 4 roles
- [ ] Test on mobile device
- [ ] Check browser console for errors

### Monitoring (First 24 Hours)
- [ ] Check Railway logs for errors
- [ ] Monitor MongoDB Atlas metrics
- [ ] Test with multiple users
- [ ] Verify ML models running correctly
- [ ] Check response times

---

## 🐛 Common Issues & Solutions

### Issue: "Application failed to respond"
**Solution:** Check Railway logs, verify MONGO_URI is correct

### Issue: "Network Error" in frontend
**Solution:** 
1. Verify VITE_API_URL is correct in Vercel
2. Check FRONTEND_URL in Railway matches Vercel URL
3. Verify backend is running

### Issue: "CORS Error"
**Solution:** Update FRONTEND_URL in Railway to exact Vercel URL (including https://)

### Issue: "Authentication failed" (MongoDB)
**Solution:** 
1. Check MongoDB Atlas username/password
2. Add IP whitelist: 0.0.0.0/0 (allow all)

### Issue: "Models not loading"
**Solution:** 
1. Check Railway logs for model loading errors
2. Verify models are in repository
3. Check scikit-learn version matches (1.6.1)

---

## 📊 Success Criteria

Your deployment is successful when:

- ✅ Backend health check returns `{"status": "ok"}`
- ✅ ML health check shows all 3 models loaded
- ✅ Frontend loads without errors
- ✅ Can register and login
- ✅ Can mark attendance
- ✅ Predictions appear on dashboard
- ✅ No errors in browser console
- ✅ No errors in Railway logs

---

## 🎯 Deployment Time Estimate

| Task | Time |
|------|------|
| Push to GitHub | 5 min |
| Deploy to Railway | 10 min |
| Deploy to Vercel | 5 min |
| Update CORS | 2 min |
| Testing | 10 min |
| **Total** | **~30 min** |

---

## 📝 Quick Commands

### Generate JWT Secret
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Test Backend Locally
```bash
cd backend
python app.py
# Visit: http://localhost:5000/api/health
```

### Test Frontend Locally
```bash
cd frontend
npm run dev
# Visit: http://localhost:5173
```

### Build Frontend
```bash
cd frontend
npm run build
# Check dist/ folder created
```

### Push to GitHub
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

---

## 🎉 You're Ready!

Everything is prepared for deployment. Follow these steps:

1. ✅ Complete local testing checklist
2. 🚂 Deploy backend to Railway (10 min)
3. 🌐 Deploy frontend to Vercel (5 min)
4. 🔄 Update CORS settings (2 min)
5. ✅ Test everything (10 min)

**Total time: ~30 minutes**

---

## 📞 Need Help?

- **Deployment Guide:** See DEPLOYMENT.md
- **Project Overview:** See PROJECT_SUMMARY.md
- **Known Issues:** See AUDIT_REPORT.md
- **Fixes Applied:** See FIXES_APPLIED.md

---

**Good luck with your deployment! 🚀**

Your app is solid, well-documented, and ready to go live!
