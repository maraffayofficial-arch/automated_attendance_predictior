import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts'

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-slate-700">{formatDate(d.date)}</p>
      <p className="text-slate-600">
        Absence probability:{' '}
        <span className="font-bold" style={{ color: d.predicted_status === 'ABSENT' ? '#ef4444' : '#2563eb' }}>
          {Math.round(d.absence_probability * 100)}%
        </span>
      </p>
      <p className={`font-semibold mt-1 ${d.predicted_status === 'ABSENT' ? 'text-red-500' : 'text-green-600'}`}>
        Predicted: {d.predicted_status}
      </p>
    </div>
  )
}

export default function ForecastChart({ forecasts = [] }) {
  if (!forecasts.length) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-400 text-sm">
        No forecast data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={forecasts} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tick={{ fontSize: 12, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 1]}
          tickFormatter={(v) => `${Math.round(v * 100)}%`}
          tick={{ fontSize: 12, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0.60} stroke="#f97316" strokeDasharray="4 4" label={{ value: 'High', fontSize: 11, fill: '#f97316' }} />
        <ReferenceLine y={0.35} stroke="#eab308" strokeDasharray="4 4" label={{ value: 'Medium', fontSize: 11, fill: '#eab308' }} />
        <Bar dataKey="absence_probability" radius={[4, 4, 0, 0]} maxBarSize={40}>
          {forecasts.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.predicted_status === 'ABSENT' ? '#ef4444' : '#2563eb'}
              fillOpacity={0.85}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
