import { useNavigate } from 'react-router-dom'
import { ChevronRight, ArrowDownRight, BookOpen, Zap, Activity, Clock } from 'lucide-react'

const levelStyle = {
  CRITICAL: 'bg-red-100 text-red-700 border border-red-200',
  HIGH:     'bg-orange-100 text-orange-700 border border-orange-200',
  MEDIUM:   'bg-amber-100 text-amber-700 border border-amber-200',
  LOW:      'bg-green-100 text-green-700 border border-green-200',
}

const anomalyIcons = {
  SUDDEN_DROP:       { icon: ArrowDownRight, label: 'Sudden Drop',        color: 'text-red-500' },
  EXAM_ABSENCE:      { icon: BookOpen,       label: 'Exam Absence',        color: 'text-purple-500' },
  PERFECT_THEN_ABSENT: { icon: Zap,          label: 'Perfect→Absent',      color: 'text-yellow-500' },
  ERRATIC_PATTERN:   { icon: Activity,       label: 'Erratic Pattern',     color: 'text-blue-500' },
  PROLONGED_ABSENCE: { icon: Clock,          label: 'Prolonged Absence',   color: 'text-red-600' },
}

export default function AlertTable({ alerts = [] }) {
  const navigate = useNavigate()

  if (alerts.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-10 text-center text-slate-400">
        No alerts found for the selected filter.
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 bg-slate-50">
            <th className="text-left px-5 py-3 text-slate-500 font-medium">Person ID</th>
            <th className="text-left px-5 py-3 text-slate-500 font-medium">Level</th>
            <th className="text-left px-5 py-3 text-slate-500 font-medium">Risk Score</th>
            <th className="text-left px-5 py-3 text-slate-500 font-medium">Anomalies</th>
            <th className="text-left px-5 py-3 text-slate-500 font-medium">7-Day Absences</th>
            <th className="px-5 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50">
          {alerts.map((alert) => (
            <tr
              key={alert.person_id}
              className="hover:bg-slate-50 cursor-pointer transition-colors"
              onClick={() => navigate(`/persons/${alert.person_id}`)}
            >
              <td className="px-5 py-3.5 font-mono font-semibold text-slate-800">
                {alert.person_id}
              </td>
              <td className="px-5 py-3.5">
                <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${levelStyle[alert.alert_level]}`}>
                  {alert.alert_level}
                </span>
              </td>
              <td className="px-5 py-3.5">
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        alert.alert_level === 'CRITICAL' ? 'bg-red-500' :
                        alert.alert_level === 'HIGH'     ? 'bg-orange-500' :
                        alert.alert_level === 'MEDIUM'   ? 'bg-amber-400' : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.round(alert.combined_risk_score * 100)}%` }}
                    />
                  </div>
                  <span className="text-slate-600 tabular-nums">
                    {Math.round(alert.combined_risk_score * 100)}%
                  </span>
                </div>
              </td>
              <td className="px-5 py-3.5">
                <div className="flex flex-wrap gap-1">
                  {(alert.anomaly_types || []).map((type) => {
                    const meta = anomalyIcons[type]
                    if (!meta) return null
                    const Icon = meta.icon
                    return (
                      <span
                        key={type}
                        title={meta.label}
                        className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs"
                      >
                        <Icon size={11} className={meta.color} />
                        {meta.label}
                      </span>
                    )
                  })}
                  {(!alert.anomaly_types || alert.anomaly_types.length === 0) && (
                    <span className="text-slate-300 text-xs">—</span>
                  )}
                </div>
              </td>
              <td className="px-5 py-3.5 text-slate-600 tabular-nums">
                {alert.model_details?.xgboost?.predicted_absences_7d ?? '—'} / 7
              </td>
              <td className="px-5 py-3.5">
                <ChevronRight size={16} className="text-slate-400" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
