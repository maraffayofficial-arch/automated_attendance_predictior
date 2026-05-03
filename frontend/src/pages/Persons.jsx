import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Upload, Search, ChevronRight, Pencil, Trash2, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import ImportCSVModal from '../components/ImportCSVModal'

const levelStyle = {
  CRITICAL: 'bg-red-100 text-red-700',
  HIGH:     'bg-orange-100 text-orange-700',
  MEDIUM:   'bg-amber-100 text-amber-700',
  LOW:      'bg-green-100 text-green-700',
}

function AddPersonModal({ onClose, onSuccess }) {
  const [form, setForm] = useState({ person_id: '', name: '', type: 'employee', department: '', email: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await client.post('/persons/', form)
      onSuccess?.()
      onClose()
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to add person')
    } finally {
      setLoading(false)
    }
  }

  const fields = [
    { key: 'person_id', label: 'Person ID', placeholder: 'e.g. EMP-0001 or STU-0001', required: true },
    { key: 'name', label: 'Full Name', placeholder: 'Enter full name', required: true },
    { key: 'department', label: 'Department / Class', placeholder: 'e.g. Engineering, CS-2A' },
    { key: 'email', label: 'Email', placeholder: 'email@example.com', type: 'email' },
  ]

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 className="font-semibold text-slate-800">Add New Person</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-3">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-2.5 text-sm">{error}</div>
          )}
          {fields.map(({ key, label, placeholder, required, type }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
              <input
                type={type || 'text'}
                value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                placeholder={placeholder}
                required={required}
              />
            </div>
          ))}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="employee">Employee</option>
              <option value="student">Student</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg hover:bg-slate-50 font-medium text-sm">Cancel</button>
            <button type="submit" disabled={loading} className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white py-2 rounded-lg font-medium text-sm">
              {loading ? 'Adding...' : 'Add Person'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Persons() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [persons, setPersons] = useState([])
  const [alertMap, setAlertMap] = useState({})
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [showAdd, setShowAdd] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [deleting, setDeleting] = useState(null)

  const canEdit = user?.role === 'admin' || user?.role === 'teacher'

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (typeFilter !== 'all') params.type = typeFilter
      if (search) params.search = search

      const [personsRes, alertsRes] = await Promise.allSettled([
        client.get('/persons/', { params }),
        client.get('/predictions/'),
      ])

      if (personsRes.status === 'fulfilled') setPersons(personsRes.value.data)
      if (alertsRes.status === 'fulfilled') {
        const map = {}
        for (const a of alertsRes.value.data.alerts ?? []) map[a.person_id] = a
        setAlertMap(map)
      }
    } finally {
      setLoading(false)
    }
  }, [search, typeFilter])

  useEffect(() => {
    const t = setTimeout(fetchData, 300)
    return () => clearTimeout(t)
  }, [fetchData])

  const deletePerson = async (e, personId) => {
    e.stopPropagation()
    if (!confirm(`Delete ${personId}? This cannot be undone.`)) return
    setDeleting(personId)
    try {
      await client.delete(`/persons/${personId}`)
      setPersons((prev) => prev.filter((p) => p.person_id !== personId))
    } catch { /* ignore */ }
    finally { setDeleting(null) }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Persons</h1>
          <p className="text-slate-500 text-sm mt-0.5">{persons.length} person{persons.length !== 1 ? 's' : ''} registered</p>
        </div>
        {canEdit && (
          <div className="flex gap-2">
            <button
              onClick={() => setShowImport(true)}
              className="flex items-center gap-2 border border-slate-300 text-slate-600 hover:bg-slate-50 px-4 py-2 rounded-lg text-sm font-medium"
            >
              <Upload size={15} /> Import CSV
            </button>
            <button
              onClick={() => setShowAdd(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-semibold"
            >
              <Plus size={15} /> Add Person
            </button>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-5">
        <div className="relative flex-1 max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by ID, name, department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Types</option>
          <option value="employee">Employee</option>
          <option value="student">Student</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="spinner" /></div>
      ) : persons.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <p className="text-slate-400 text-sm">No persons found. Add one or import a CSV.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Person ID</th>
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Name</th>
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Type</th>
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Department</th>
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Risk Level</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {persons.map((p) => {
                const alert = alertMap[p.person_id]
                return (
                  <tr
                    key={p._id}
                    className="hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/persons/${p.person_id}`)}
                  >
                    <td className="px-5 py-3.5 font-mono font-semibold text-slate-800">{p.person_id}</td>
                    <td className="px-5 py-3.5 text-slate-700">{p.name}</td>
                    <td className="px-5 py-3.5">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        p.type === 'student' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                      }`}>
                        {p.type}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-500">{p.department || '—'}</td>
                    <td className="px-5 py-3.5">
                      {alert ? (
                        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${levelStyle[alert.alert_level]}`}>
                          {alert.alert_level}
                        </span>
                      ) : (
                        <span className="text-slate-300 text-xs">No data</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2 justify-end">
                        {canEdit && (
                          <button
                            onClick={(e) => { e.stopPropagation(); deletePerson(e, p.person_id) }}
                            disabled={deleting === p.person_id}
                            className="text-slate-300 hover:text-red-500 transition-colors p-1"
                            title="Delete"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                        <ChevronRight size={16} className="text-slate-400" />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && <AddPersonModal onClose={() => setShowAdd(false)} onSuccess={fetchData} />}
      {showImport && <ImportCSVModal type="persons" onClose={() => setShowImport(false)} onSuccess={fetchData} />}
    </div>
  )
}
