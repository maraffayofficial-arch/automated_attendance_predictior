import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import { Calendar, Check, X, Save, AlertCircle, Users, TrendingUp } from 'lucide-react'

export default function DailyAttendance() {
  const { user } = useAuth()
  const [persons, setPersons] = useState([])
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [attendance, setAttendance] = useState({})
  const [isExamPeriod, setIsExamPeriod] = useState(false)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [todayStats, setTodayStats] = useState(null)
  const [filter, setFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadPersons()
    loadTodayStats()
  }, [])

  useEffect(() => {
    loadExistingAttendance()
  }, [selectedDate])

  const loadPersons = async () => {
    setLoading(true)
    try {
      const res = await client.get('/persons/')
      setPersons(res.data)
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to load persons' })
    } finally {
      setLoading(false)
    }
  }

  const loadExistingAttendance = async () => {
    try {
      const res = await client.get(`/attendance/date/${selectedDate}`)
      const existing = {}
      res.data.forEach(rec => {
        existing[rec.person_id] = rec.attendance_binary
        if (rec.is_exam_period === 1) {
          setIsExamPeriod(true)
        }
      })
      setAttendance(existing)
    } catch (err) {
      console.error('Failed to load existing attendance:', err)
    }
  }

  const loadTodayStats = async () => {
    try {
      const res = await client.get('/attendance/stats/today')
      setTodayStats(res.data)
    } catch (err) {
      console.error('Failed to load today stats:', err)
    }
  }

  const handleAttendanceChange = (personId, value) => {
    setAttendance(prev => ({ ...prev, [personId]: value }))
  }

  const handleMarkAll = (value) => {
    const newAttendance = {}
    filteredPersons.forEach(p => {
      newAttendance[p.person_id] = value
    })
    setAttendance(prev => ({ ...prev, ...newAttendance }))
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)

    const records = Object.entries(attendance).map(([person_id, attendance_binary]) => ({
      person_id,
      attendance_binary
    }))

    if (records.length === 0) {
      setMessage({ type: 'error', text: 'Please mark attendance for at least one person' })
      setSaving(false)
      return
    }

    try {
      const res = await client.post('/attendance/daily', {
        date: selectedDate,
        records,
        is_exam_period: isExamPeriod ? 1 : 0
      })

      setMessage({
        type: 'success',
        text: `Attendance saved! ${res.data.inserted} inserted, ${res.data.updated} updated`
      })

      if (selectedDate === new Date().toISOString().split('T')[0]) {
        loadTodayStats()
      }
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || 'Failed to save attendance'
      })
    } finally {
      setSaving(false)
    }
  }

  const filteredPersons = persons.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         p.person_id.toLowerCase().includes(searchQuery.toLowerCase())

    if (filter === 'all') return matchesSearch
    if (filter === 'marked') return matchesSearch && attendance[p.person_id] !== undefined
    if (filter === 'unmarked') return matchesSearch && attendance[p.person_id] === undefined
    if (filter === 'present') return matchesSearch && attendance[p.person_id] === 1
    if (filter === 'absent') return matchesSearch && attendance[p.person_id] === 0
    return matchesSearch
  })

  const stats = {
    total: persons.length,
    marked: Object.keys(attendance).length,
    present: Object.values(attendance).filter(v => v === 1).length,
    absent: Object.values(attendance).filter(v => v === 0).length,
    unmarked: persons.length - Object.keys(attendance).length
  }

  const attendanceRate = stats.marked > 0 ? ((stats.present / stats.marked) * 100).toFixed(1) : 0
  const canEdit = user?.role === 'admin' || user?.role === 'teacher'

  if (!canEdit) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
          <AlertCircle className="mx-auto text-yellow-500 mb-4" size={48} />
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Access Restricted</h2>
          <p className="text-gray-600">Only admins and teachers can record attendance.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Daily Attendance</h1>
        <p className="text-gray-600">Mark attendance for all persons</p>
      </div>

      {/* Today's Stats */}
      {todayStats && selectedDate === new Date().toISOString().split('T')[0] && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Persons</p>
                <p className="text-2xl font-bold text-gray-900">{todayStats.total_persons}</p>
              </div>
              <Users className="text-blue-500" size={24} />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Present</p>
                <p className="text-2xl font-bold text-gray-900">{todayStats.present}</p>
              </div>
              <Check className="text-green-500" size={24} />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Absent</p>
                <p className="text-2xl font-bold text-gray-900">{todayStats.absent}</p>
              </div>
              <X className="text-red-500" size={24} />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Not Marked</p>
                <p className="text-2xl font-bold text-gray-900">{todayStats.not_marked}</p>
              </div>
              <AlertCircle className="text-yellow-500" size={24} />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Attendance Rate</p>
                <p className="text-2xl font-bold text-gray-900">{todayStats.attendance_rate}%</p>
              </div>
              <TrendingUp className="text-purple-500" size={24} />
            </div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Calendar className="inline mr-2" size={16} />
              Date
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search
            </label>
            <input
              type="text"
              placeholder="Search by name or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter
            </label>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All ({persons.length})</option>
              <option value="marked">Marked ({stats.marked})</option>
              <option value="unmarked">Unmarked ({stats.unmarked})</option>
              <option value="present">Present ({stats.present})</option>
              <option value="absent">Absent ({stats.absent})</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isExamPeriod}
              onChange={(e) => setIsExamPeriod(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm font-medium text-gray-700">Exam Period</span>
          </label>

          <div className="flex-1" />

          <button
            onClick={() => handleMarkAll(1)}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
          >
            <Check size={16} />
            Mark All Present
          </button>

          <button
            onClick={() => handleMarkAll(0)}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
          >
            <X size={16} />
            Mark All Absent
          </button>
        </div>
      </div>

      {/* Current Selection Stats */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-700">
            <strong>{stats.marked}</strong> of <strong>{stats.total}</strong> marked
          </span>
          <span className="text-gray-700">
            Present: <strong className="text-green-600">{stats.present}</strong> |
            Absent: <strong className="text-red-600 ml-2">{stats.absent}</strong> |
            Rate: <strong className="text-blue-600 ml-2">{attendanceRate}%</strong>
          </span>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`mb-6 p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {message.text}
        </div>
      )}

      {/* Attendance List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Person ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Department
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Attendance
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-gray-500">
                    Loading persons...
                  </td>
                </tr>
              ) : filteredPersons.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-gray-500">
                    No persons found
                  </td>
                </tr>
              ) : (
                filteredPersons.map(person => (
                  <tr key={person.person_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {person.person_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {person.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 capitalize">
                      {person.type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {person.department}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleAttendanceChange(person.person_id, 1)}
                          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                            attendance[person.person_id] === 1
                              ? 'bg-green-600 text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-green-100'
                          }`}
                        >
                          <Check size={16} className="inline mr-1" />
                          Present
                        </button>
                        <button
                          onClick={() => handleAttendanceChange(person.person_id, 0)}
                          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                            attendance[person.person_id] === 0
                              ? 'bg-red-600 text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-red-100'
                          }`}
                        >
                          <X size={16} className="inline mr-1" />
                          Absent
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Save Button */}
      <div className="mt-6 flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving || stats.marked === 0}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-lg font-medium"
        >
          <Save size={20} />
          {saving ? 'Saving...' : 'Save Attendance'}
        </button>
      </div>
    </div>
  )
}
