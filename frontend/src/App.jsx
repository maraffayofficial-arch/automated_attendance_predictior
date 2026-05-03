import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Persons from './pages/Persons'
import PersonDetail from './pages/PersonDetail'
import DailyAttendance from './pages/DailyAttendance'
import AttendanceHistory from './pages/AttendanceHistory'
import SelfAttendance from './pages/SelfAttendance'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="flex items-center justify-center h-screen">
      <div className="spinner" />
    </div>
  )
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="attendance/self" element={<SelfAttendance />} />
        <Route path="attendance/daily" element={<DailyAttendance />} />
        <Route path="attendance/history" element={<AttendanceHistory />} />
        <Route path="persons" element={<Persons />} />
        <Route path="persons/:personId" element={<PersonDetail />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
