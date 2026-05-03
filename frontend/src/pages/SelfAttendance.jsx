import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import { Calendar, Check, X, Clock, TrendingUp, AlertCircle } from 'lucide-react'

export default function SelfAttendance() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [todayStatus, setTodayStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [marking, setMarking] = useState(false)
  const [message, setMessage] = useState(null)
  const [prediction, setPrediction] = useState(null)
  const [recentHistory, setRecentHistory] = useState([])

  useEffect(() => {
    if (user?.role !== 'person') {
      navigate('/dashboard')
      return
    }
    loadData()
  }, [user, navigate])

  const loadData = async () => {
    setLoading(true)
    try {
      const [statusRes, predRes, historyRes] = await Promise.allSettled([
        client.get('/attendance/self/today'),
        client.get(`/predictions/${user.person_id}`),
        client.get('/attendance/', { params: { limit: 7 } })
      ])

      if (statusRes.status === 'fulfilled') {
        setTodayStatus(statusRes.value.data)
      }

      if (predRes.status === 'fulfilled') {
        setPrediction(predRes.value.data)
      }

      if (historyRes.status === 'fulfilled') {
        setRecentHistory(historyRes.value.data)
      }
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setLoading(false)
    }
  }

  const markAttendance = async (status) => {
    setMarking(true)
    setMessage(null)

    try {
      await client.post('/attendance/self', {
        attendance_binary: status
      })

      setMessage({
        type: 'success',
        text: `Marked as ${status === 1 ? 'Present' : 'Absent'} successfully!`
      })

      await loadData()
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || 'Failed to mark attendance'
      })
    } finally {
      setMarking(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="spinner" />
      </div>
    )
  }

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })

  const attendanceRate = recentHistory.length > 0
    ? ((recentHistory.filter(r => r.attendance_binary === 1).length / recentHistory.length) * 100).toFixed(1)
    : 0

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">My Attendance</h1>
        <p className="text-gray-600">Welcome, {user?.username}</p>
      </div>

      {/* Message */}
      {message && (
        <div className={`mb-6 p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {message.text}
        </div>
      )}

      {/* Today's Attendance */}
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <Calendar className="text-blue-600" size={24} />
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Today's Attendance</h2>
            <p className="text-sm text-gray-600">{today}</p>
          </div>
        </div>

        {todayStatus?.marked ? (
          <div className="text-center py-8">
            <div className={`inline-flex items-center gap-2 px-6 py-3 rounded-full text-lg font-bold ${
              todayStatus.attendance_binary === 1
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-700'
            }`}>
              {todayStatus.attendance_binary === 1 ? (
                <>
                  <Check size={24} />
                  Marked Present
                </>
              ) : (
                <>
                  <X size={24} />
                  Marked Absent
                </>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-3">
              Marked at {new Date(todayStatus.created_at).toLocaleTimeString()}
            </p>
            <button
              onClick={() => markAttendance(todayStatus.attendance_binary === 1 ? 0 : 1)}
              disabled={marking}
              className="mt-4 text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Change to {todayStatus.attendance_binary === 1 ? 'Absent' : 'Present'}
            </button>
          </div>
        ) : (
          <div className="text-center py-8">
            <Clock className="mx-auto text-gray-300 mb-4" size={48} />
            <p className="text-gray-600 mb-6">You haven't marked your attendance today</p>
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={() => markAttendance(1)}
                disabled={marking}
                className="px-8 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition-colors flex items-center gap-2 text-lg font-semibold"
              >
                <Check size={20} />
                Mark Present
              </button>
              <button
                onClick={() => markAttendance(0)}
                disabled={marking}
                className="px-8 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 transition-colors flex items-center gap-2 text-lg font-semibold"
              >
                <X size={20} />
                Mark Absent
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Attendance Rate</p>
              <p className="text-2xl font-bold text-gray-900">{attendanceRate}%</p>
              <p className="text-xs text-gray-500 mt-1">Last 7 days</p>
            </div>
            <TrendingUp className="text-blue-500" size={24} />
          </div>
        </div>

        {prediction && (
          <>
            <div className="bg-white rounded-lg shadow p-4 border-l-4 border-orange-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Risk Level</p>
                  <p className={`text-xl font-bold ${
                    prediction.alert_level === 'CRITICAL' ? 'text-red-700' :
                    prediction.alert_level === 'HIGH' ? 'text-orange-700' :
                    prediction.alert_level === 'MEDIUM' ? 'text-amber-700' :
                    'text-green-700'
                  }`}>
                    {prediction.alert_level}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {Math.round(prediction.combined_risk_score * 100)}% risk score
                  </p>
                </div>
                <AlertCircle className="text-orange-500" size={24} />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Next 7 Days</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {prediction.model_details?.xgboost?.predicted_absences_7d || 0}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Predicted absences</p>
                </div>
                <Calendar className="text-purple-500" size={24} />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Recent History */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent History</h2>
        </div>
        <div className="p-6">
          {recentHistory.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No attendance records yet</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recentHistory.map(record => (
                <div
                  key={record._id}
                  className={`p-4 rounded-lg border-2 ${
                    record.attendance_binary === 1
                      ? 'border-green-200 bg-green-50'
                      : 'border-red-200 bg-red-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">
                      {new Date(record.date).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                      })}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs font-bold ${
                      record.attendance_binary === 1
                        ? 'bg-green-600 text-white'
                        : 'bg-red-600 text-white'
                    }`}>
                      {record.attendance_binary === 1 ? 'PRESENT' : 'ABSENT'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
