import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  ArrowLeft, Plus, Upload, Trash2,
  ArrowDownRight, BookOpen, Zap, Activity, Clock,
} from 'lucide-react'
import client from '../api/client'
import ForecastChart from '../components/ForecastChart'
import AddAttendanceModal from '../components/AddAttendanceModal'
import ImportCSVModal from '../components/ImportCSVModal'

const levelStyle = {
  CRITICAL: { ring: 'critical', badge: 'bg-red-100 text-red-700 border border-red-200' },
  HIGH:     { ring: 'high',     badge: 'bg-orange-100 text-orange-700 border border-orange-200' },
  MEDIUM:   { ring: 'medium',   badge: 'bg-amber-100 text-amber-700 border border-amber-200' },
  LOW:      { ring: 'low',      badge: 'bg-green-100 text-green-700 border border-green-200' },
}

const anomalyMeta = {
  SUDDEN_DROP:         { icon: ArrowDownRight, label: 'Sudden Drop',       color: 'text-red-500',    bg: 'bg-red-50' },
  EXAM_ABSENCE:        { icon: BookOpen,       label: 'Exam Absence',      color: 'text-purple-600', bg: 'bg-purple-50' },
  PERFECT_THEN_ABSENT: { icon: Zap,            label: 'Perfect→Absent',    color: 'text-yellow-600', bg: 'bg-yellow-50' },
  ERRATIC_PATTERN:     { icon: Activity,       label: 'Erratic Pattern',   color: 'text-blue-600',   bg: 'bg-blue-50' },
  PROLONGED_ABSENCE:   { icon: Clock,          label: 'Prolonged Absence', color: 'text-red-600',    bg: 'bg-red-50' },
}

export default function PersonDetail() {
  const { personId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [person, setPerson] = useState(null)
  const [alert, setAlert] = useState(null)
  const [attendance, setAttendance] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  // Check if user can edit (admin/teacher can edit, persons cannot)
  const canEdit = user?.role === 'admin' || user?.role === 'teacher'

  // Persons can only view their own details
  useEffect(() => {
    if (user?.role === 'person' && user?.person_id !== personId) {
      navigate('/attendance/self')
    }
  }, [user, personId, navigate])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [personRes, alertRes, attendRes] = await Promise.allSettled([
        client.get(`/persons/${personId}`),
        client.get(`/predictions/${personId}`),
        client.get('/attendance/', { params: { person_id: personId } }),
      ])
      if (personRes.status === 'fulfilled') setPerson(personRes.value.data)
      if (alertRes.status === 'fulfilled')  setAlert(alertRes.value.data)
      if (attendRes.status === 'fulfilled') setAttendance(attendRes.value.data)
    } finally {
      setLoading(false)
    }
  }, [personId])

  useEffect(() => { fetchData() }, [fetchData])

  const deleteRecord = async (id) => {
    if (!confirm('Delete this attendance record?')) return
    setDeletingId(id)
    try {
      await client.delete(`/attendance/${id}`)
      setAttendance((prev) => prev.filter((r) => r._id !== id))
    } catch { /* ignore */ }
    finally { setDeletingId(null) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full py-20"><div className="spinner" /></div>
  )

  // Show "not found" only if there is truly nothing — no profile, no alert, no attendance
  if (!person && !alert && attendance.length === 0) return (
    <div className="p-6 text-center">
      <p className="text-slate-500">No data found for <span className="font-mono font-semibold">{personId}</span>.</p>
      <button onClick={() => navigate('/dashboard')} className="mt-3 text-blue-600 text-sm">← Back to Dashboard</button>
    </div>
  )

  const displayName = person?.name || personId
  const levelMeta = alert ? (levelStyle[alert.alert_level] ?? levelStyle.LOW) : null
  const riskPct = alert ? Math.round(alert.combined_risk_score * 100) : null

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <button
        onClick={() => navigate('/persons')}
        className="flex items-center gap-1.5 text-slate-500 hover:text-blue-600 text-sm mb-5 transition-colors"
      >
        <ArrowLeft size={15} /> Back to Persons
      </button>

      {/* Person header */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-slate-800">{displayName}</h1>
              {alert && (
                <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${levelMeta.badge}`}>
                  {alert.alert_level}
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 text-sm text-slate-500">
              <span className="font-mono font-semibold text-slate-700">{personId}</span>
              {person?.type && (
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  person.type === 'student' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                }`}>{person.type}</span>
              )}
              {person?.department && <span>{person.department}</span>}
              {person?.email && <span>{person.email}</span>}
              {!person && (
                <span className="text-amber-500 text-xs">No profile — add this person to the Persons list to include their name</span>
              )}
            </div>
          </div>
          {alert && (
            <div className={`risk-ring ${levelMeta.ring}`}>
              {riskPct}%
            </div>
          )}
        </div>
      </div>

      {alert ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
          {/* Anomalies & Reasons */}
          <div className="bg-white rounded-xl shadow-sm p-5 space-y-4">
            {/* Anomaly types */}
            {alert.anomaly_types?.length > 0 && (
              <div>
                <p className="text-sm font-semibold text-slate-600 mb-2">Anomaly Types</p>
                <div className="flex flex-wrap gap-2">
                  {alert.anomaly_types.map((type) => {
                    const meta = anomalyMeta[type]
                    if (!meta) return null
                    const Icon = meta.icon
                    return (
                      <span key={type} className={`flex items-center gap-1.5 ${meta.bg} px-3 py-1.5 rounded-lg text-sm font-medium ${meta.color}`}>
                        <Icon size={14} /> {meta.label}
                      </span>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Model details */}
            <div>
              <p className="text-sm font-semibold text-slate-600 mb-2">Model Details</p>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Absence Prob.', value: `${Math.round((alert.model_details?.xgboost?.absence_probability ?? 0) * 100)}%` },
                  { label: 'Predicted Absent', value: `${alert.model_details?.xgboost?.predicted_absences_7d ?? '—'} / 7 days` },
                  { label: 'Exam Absence Rate', value: alert.model_details?.exam_check?.has_exam_absence
                    ? `${Math.round((alert.model_details.exam_check.exam_absence_rate ?? 0) * 100)}%`
                    : 'None' },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-slate-50 rounded-lg p-3">
                    <p className="text-xs text-slate-500 mb-1">{label}</p>
                    <p className="text-sm font-bold text-slate-800">{value}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Reasons */}
            {alert.reasons?.length > 0 && (
              <div>
                <p className="text-sm font-semibold text-slate-600 mb-2">Reasons</p>
                <ul className="space-y-1.5">
                  {alert.reasons.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Recommended actions */}
          <div className="bg-white rounded-xl shadow-sm p-5">
            <p className="text-sm font-semibold text-slate-600 mb-3">Recommended Actions</p>
            {alert.recommended_actions?.length > 0 ? (
              <ul className="space-y-2">
                {alert.recommended_actions.map((action, i) => (
                  <li key={i} className="flex items-start gap-3 bg-blue-50 rounded-lg p-3 text-sm text-slate-700">
                    <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    {action}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-400 text-sm">No actions recommended.</p>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-5 text-sm text-blue-700">
          No alert data for this person in the latest analysis run.
        </div>
      )}

      {/* Forecast chart */}
      {alert?.daily_forecasts?.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-5 mb-5">
          <p className="text-sm font-semibold text-slate-600 mb-4">7-Day Absence Probability Forecast</p>
          <ForecastChart forecasts={alert.daily_forecasts} />
          <div className="flex gap-4 mt-3 text-xs text-slate-500">
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-red-500 inline-block" /> Predicted Absent</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-blue-600 inline-block" /> Predicted Present</span>
            <span className="flex items-center gap-1.5 border-t-2 border-orange-400 border-dashed pt-0" style={{ borderTop: 'none', borderLeft: 'none' }}>
              <span className="w-5 border-t-2 border-dashed border-orange-400" /> High threshold (60%)
            </span>
          </div>
        </div>
      )}

      {/* Attendance history */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <p className="font-semibold text-slate-700">Attendance History ({attendance.length} records)</p>
          {canEdit && (
            <div className="flex gap-2">
              <button
                onClick={() => setShowImport(true)}
                className="flex items-center gap-1.5 border border-slate-300 text-slate-600 hover:bg-slate-50 px-3 py-1.5 rounded-lg text-xs font-medium"
              >
                <Upload size={13} /> Import CSV
              </button>
              <button
                onClick={() => setShowAdd(true)}
                className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold"
              >
                <Plus size={13} /> Add Record
              </button>
            </div>
          )}
        </div>

        {attendance.length === 0 ? (
          <div className="p-10 text-center text-slate-400 text-sm">No attendance records found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Date</th>
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Status</th>
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Exam Period</th>
                {canEdit && <th className="px-5 py-3" />}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {attendance.map((r) => (
                <tr key={r._id} className="hover:bg-slate-50">
                  <td className="px-5 py-3 text-slate-700 font-mono">{r.date}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                      r.attendance_binary === 1
                        ? 'bg-green-100 text-green-700'
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {r.attendance_binary === 1 ? 'Present' : 'Absent'}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-slate-500">
                    {r.is_exam_period === 1 ? (
                      <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded text-xs font-medium">Exam</span>
                    ) : '—'}
                  </td>
                  {canEdit && (
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => deleteRecord(r._id)}
                        disabled={deletingId === r._id}
                        className="text-slate-300 hover:text-red-500 transition-colors p-1"
                      >
                        <Trash2 size={13} />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showAdd && (
        <AddAttendanceModal
          personId={personId}
          onClose={() => setShowAdd(false)}
          onSuccess={fetchData}
        />
      )}
      {showImport && (
        <ImportCSVModal
          type="attendance"
          onClose={() => setShowImport(false)}
          onSuccess={fetchData}
        />
      )}
    </div>
  )
}
