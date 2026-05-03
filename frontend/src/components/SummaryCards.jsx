import { AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react'

const levels = [
  {
    key: 'critical',
    label: 'Critical',
    icon: AlertTriangle,
    bg: 'bg-red-50',
    border: 'border-red-500',
    text: 'text-red-600',
    iconBg: 'bg-red-100',
  },
  {
    key: 'high',
    label: 'High Risk',
    icon: AlertCircle,
    bg: 'bg-orange-50',
    border: 'border-orange-500',
    text: 'text-orange-600',
    iconBg: 'bg-orange-100',
  },
  {
    key: 'medium',
    label: 'Medium Risk',
    icon: Info,
    bg: 'bg-amber-50',
    border: 'border-amber-400',
    text: 'text-amber-600',
    iconBg: 'bg-amber-100',
  },
  {
    key: 'low',
    label: 'Low Risk',
    icon: CheckCircle,
    bg: 'bg-green-50',
    border: 'border-green-500',
    text: 'text-green-600',
    iconBg: 'bg-green-100',
  },
]

export default function SummaryCards({ summary, onFilterChange, activeFilter }) {
  if (!summary) return null

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {levels.map(({ key, label, icon: Icon, bg, border, text, iconBg }) => {
        const count = summary[key] ?? 0
        const isActive = activeFilter === key.toUpperCase()
        return (
          <button
            key={key}
            onClick={() => onFilterChange(isActive ? 'ALL' : key.toUpperCase())}
            className={`${bg} border-l-4 ${border} rounded-xl p-5 text-left shadow-sm hover:shadow-md transition-all ${
              isActive ? 'ring-2 ring-offset-1 ring-blue-400' : ''
            }`}
          >
            <div className={`${iconBg} w-10 h-10 rounded-lg flex items-center justify-center mb-3`}>
              <Icon className={text} size={20} />
            </div>
            <p className="text-3xl font-bold text-slate-800">{count}</p>
            <p className={`text-sm font-medium ${text} mt-0.5`}>{label}</p>
            <p className="text-xs text-slate-400 mt-1">
              {summary.total_persons ? Math.round((count / summary.total_persons) * 100) : 0}% of total
            </p>
          </button>
        )
      })}
    </div>
  )
}
