import { useState } from 'react'
import { X } from 'lucide-react'
import client from '../api/client'

export default function AddAttendanceModal({ personId, onClose, onSuccess }) {
  const today = new Date().toISOString().split('T')[0]
  const [form, setForm] = useState({
    person_id: personId || '',
    date: today,
    attendance_binary: 1,
    is_exam_period: 0,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await client.post('/attendance/', {
        ...form,
        attendance_binary: Number(form.attendance_binary),
        is_exam_period: Number(form.is_exam_period),
      })
      onSuccess?.()
      onClose()
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to add record')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 className="font-semibold text-slate-800">Add Attendance Record</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-2.5 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Person ID</label>
            <input
              type="text"
              value={form.person_id}
              onChange={(e) => setForm({ ...form, person_id: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. EMP-0001"
              required
              readOnly={!!personId}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Date</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Attendance Status</label>
            <div className="flex gap-3">
              {[{ val: 1, label: 'Present', color: 'border-green-500 bg-green-50 text-green-700' },
                { val: 0, label: 'Absent',  color: 'border-red-500 bg-red-50 text-red-700' }].map(({ val, label, color }) => (
                <button
                  key={val}
                  type="button"
                  onClick={() => setForm({ ...form, attendance_binary: val })}
                  className={`flex-1 py-2 rounded-lg border-2 font-medium text-sm transition-all ${
                    form.attendance_binary === val ? color : 'border-slate-200 text-slate-500 hover:border-slate-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.is_exam_period === 1}
              onChange={(e) => setForm({ ...form, is_exam_period: e.target.checked ? 1 : 0 })}
              className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-slate-700">Is exam period</span>
          </label>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg hover:bg-slate-50 font-medium text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white py-2 rounded-lg font-medium text-sm transition-colors"
            >
              {loading ? 'Saving...' : 'Add Record'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
