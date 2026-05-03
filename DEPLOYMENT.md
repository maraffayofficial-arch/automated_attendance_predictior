# Deployment Guide: Railway + Vercel + MongoDB Atlas

This guide will help you deploy the Attendance Predictor application using Railway (backend), Vercel (frontend), and MongoDB Atlas (database).

---

## 📋 Prerequisites

1. **GitHub Account** - To push your code
2. **Railway Account** - Sign up at https://railway.app
3. **Vercel Account** - Sign up at https://vercel.com
4. **MongoDB Atlas Account** - Already set up ✅

---

## 🗄️ Step 1: Prepare MongoDB Atlas

1. Go to your MongoDB Atlas dashboard
2. Click **"Connect"** on your cluster
3. Choose **"Connect your application"**
4. Copy the connection string (looks like):
   ```
   mongodb+srv://username:password@cluster.mongodb.net/attendance_db?retryWrites=true&w=majority
   ```
5. Replace `<password>` with your actual password
6. Keep this connection string handy - you'll need it for Railway

---

## 🚂 Step 2: Deploy Backend to Railway

### 2.1 Push Code to GitHub

```bash
cd C:\Users\HP\Downloads\attendance_predictor_

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit - Attendance Predictor"

# Create a new repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/attendance-predictor.git
git branch -M main
git push -u origin main
```

### 2.2 Deploy on Railway

1. Go to https://railway.app
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `attendance-predictor` repository
5. Railway will auto-detect it's a Python app

### 2.3 Configure Backend Root Directory

1. In Railway project settings, click **"Settings"**
2. Set **Root Directory** to: `backend`
3. Click **"Save"**

### 2.4 Add Environment Variables

In Railway project, go to **"Variables"** tab and add:

```
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/attendance_db?retryWrites=true&w=majority
JWT_SECRET_KEY=your-super-secret-random-string-here
FRONTEND_URL=https://your-app.vercel.app
```

**Generate JWT Secret:**
```bash
# Run this in terminal to generate a random secret
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2.5 Deploy

1. Railway will automatically deploy
2. Wait for build to complete (~3-5 minutes)
3. Once deployed, click **"Settings"** → **"Generate Domain"**
4. Copy your Railway URL (e.g., `https://attendance-backend-production.up.railway.app`)

---

## 🌐 Step 3: Deploy Frontend to Vercel

### 3.1 Create .env.production file

In `frontend/` directory, create `.env.production`:

```bash
cd frontend
echo "VITE_API_URL=https://your-railway-backend-url.railway.app/api" > .env.production
```

Replace `your-railway-backend-url` with your actual Railway URL from Step 2.5

### 3.2 Push Frontend Changes

```bash
git add .
git commit -m "Add production environment config"
git push
```

### 3.3 Deploy on Vercel

1. Go to https://vercel.com
2. Click **"Add New Project"**
3. Import your GitHub repository
4. Configure project:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`

### 3.4 Add Environment Variable

In Vercel project settings:
1. Go to **"Settings"** → **"Environment Variables"**
2. Add:
   ```
   VITE_API_URL=https://your-railway-backend-url.railway.app/api
   ```
3. Click **"Save"**

### 3.5 Deploy

1. Click **"Deploy"**
2. Wait for build (~2-3 minutes)
3. Once deployed, copy your Vercel URL (e.g., `https://attendance-predictor.vercel.app`)

---

## 🔄 Step 4: Update CORS Settings

### 4.1 Update Railway Backend

Go back to Railway and update the `FRONTEND_URL` variable:

```
FRONTEND_URL=https://your-actual-vercel-url.vercel.app
```

This allows your frontend to communicate with the backend.

### 4.2 Redeploy Backend

Railway will automatically redeploy when you change environment variables.

---

## ✅ Step 5: Test Your Deployment

### 5.1 Test Backend

Visit: `https://your-railway-url.railway.app/api/health`

You should see:
```json
{
  "status": "ok",
  "db": "attendance_db"
}
```

### 5.2 Test Frontend

1. Visit your Vercel URL: `https://your-app.vercel.app`
2. Try to register a new person account
3. Login and mark attendance
4. Check if predictions are working

---

## 🎯 Final Checklist

- [ ] MongoDB Atlas connection string is correct
- [ ] Backend deployed on Railway with correct environment variables
- [ ] Frontend deployed on Vercel with correct API URL
- [ ] CORS is configured with your Vercel URL
- [ ] Health endpoint returns success
- [ ] Can register and login
- [ ] Can mark attendance
- [ ] ML predictions are working

---

## 🐛 Troubleshooting

### Backend Issues

**Problem:** "Application failed to respond"
- Check Railway logs: Click on deployment → "View Logs"
- Verify `MONGO_URI` is correct
- Ensure all dependencies are in `requirements.txt`

**Problem:** "Module not found"
- Check if `requirements.txt` includes all packages
- Redeploy: Settings → Redeploy

### Frontend Issues

**Problem:** "Network Error" or "Failed to fetch"
- Check `VITE_API_URL` in Vercel environment variables
- Verify Railway backend is running
- Check browser console for CORS errors

**Problem:** CORS Error
- Update `FRONTEND_URL` in Railway to match your Vercel URL exactly
- Redeploy backend after changing

### Database Issues

**Problem:** "MongoServerError: Authentication failed"
- Check MongoDB Atlas username/password
- Verify IP whitelist: Atlas → Network Access → Add `0.0.0.0/0` (allow all)

---

## 💰 Cost Breakdown

| Service | Free Tier | Your Usage | Cost |
|---------|-----------|------------|------|
| **Railway** | $5 credit/month | Backend (~$3-4/month) | **$0** (within free credit) |
| **Vercel** | Unlimited | Frontend | **$0** |
| **MongoDB Atlas** | 512 MB | Database | **$0** |
| **Total** | | | **$0/month** |

---

## 🔄 Future Updates

### Update Backend Code

```bash
git add .
git commit -m "Update backend"
git push
```

Railway will auto-deploy.

### Update Frontend Code

```bash
git add .
git commit -m "Update frontend"
git push
```

Vercel will auto-deploy.

---

## 📞 Support

If you encounter issues:
1. Check Railway logs
2. Check Vercel deployment logs
3. Check browser console (F12)
4. Verify all environment variables are set correctly

---

## 🎉 Success!

Your Attendance Predictor is now live at:
- **Frontend:** https://your-app.vercel.app
- **Backend:** https://your-backend.railway.app

Share the frontend URL with your users to start using the system!
