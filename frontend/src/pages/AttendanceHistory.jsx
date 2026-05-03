import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import { Calendar, Download, TrendingUp, BarChart3 } from 'lucide-react'

export default function AttendanceHistory() {
  const { user } = useAuth()
  const [weeklyStats, setWeeklyStats] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedPerson, setSelectedPerson] = useState(null)
  const [persons, setPersons] = useState([])
  const [personHistory, setPersonHistory] = useState([])

  useEffect(() => {
    loadWeeklyStats()
    loadPersons()
  }, [])

  // For persons role, auto-select their own ID
  useEffect(() => {
    if (user?.role === 'person' && user?.person_id) {
      setSelectedPerson(user.person_id)
      loadPersonHistory(user.person_id)
    }
  }, [user])

  const loadWeeklyStats = async () => {
    setLoading(true)
    try {
      const res = await client.get('/attendance/stats/weekly')
      setWeeklyStats(res.data)
    } catch (err) {
      console.error('Failed to load weekly stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadPersons = async () => {
    try {
      const res = await client.get('/persons/')
      setPersons(res.data)
    } catch (err) {
      console.error('Failed to load persons:', err)
    }
  }

  const loadPersonHistory = async (personId) => {
    try {
      const res = await client.get('/attendance/', { params: { person_id: personId, limit: 30 } })
      setPersonHistory(res.data)
    } catch (err) {
      console.error('Failed to load person history:', err)
    }
  }

  const handlePersonSelect = (personId) => {
    setSelectedPerson(personId)
    if (personId) {
      loadPersonHistory(personId)
    } else {
      setPersonHistory([])
    }
  }

  const exportToCSV = () => {
    const headers = ['Date', 'Present', 'Absent', 'Total', 'Attendance Rate (%)']
    const rows = weeklyStats.map(stat => [
      stat.date,
      stat.present,
      stat.absent,
      stat.total,
      stat.attendance_rate
    ])

    const csv = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `attendance_history_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  const avgAttendanceRate = weeklyStats.length > 0
    ? (weeklyStats.reduce((sum, stat) => sum + stat.attendance_rate, 0) / weeklyStats.length).toFixed(1)
    : 0

  const totalPresent = weeklyStats.reduce((sum, stat) => sum + stat.present, 0)
  const totalAbsent = weeklyStats.reduce((sum, stat) => sum + stat.absent, 0)
  const totalRecords = totalPresent + totalAbsent

  // Hide weekly stats for persons (they only see their own history)
  const showWeeklyStats = user?.role !== 'person'

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Attendance History</h1>
          <p className="text-gray-600">
            {user?.role === 'person' ? 'View your attendance records' : 'View past attendance records and trends'}
          </p>
        </div>
        {showWeeklyStats && (
          <button
            onClick={exportToCSV}
            disabled={weeklyStats.length === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Download size={16} />
            Export CSV
          </button>
        )}
      </div>

      {/* Summary Cards - only for non-person users */}
      {showWeeklyStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Avg Attendance Rate</p>
                <p className="text-2xl font-bold text-gray-900">{avgAttendanceRate}%</p>
              </div>
              <TrendingUp className="text-blue-500" size={24} />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Present</p>
              <p className="text-2xl font-bold text-gray-900">{totalPresent}</p>
            </div>
            <BarChart3 className="text-green-500" size={24} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Absent</p>
              <p className="text-2xl font-bold text-gray-900">{totalAbsent}</p>
            </div>
            <BarChart3 className="text-red-500" size={24} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Records</p>
              <p className="text-2xl font-bold text-gray-900">{totalRecords}</p>
            </div>
            <Calendar className="text-purple-500" size={24} />
          </div>
        </div>
      </div>
      )}

      {/* Weekly Stats Table - only for non-person users */}
      {showWeeklyStats && (
        <div className="bg-white rounded-lg shadow mb-6">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Last 7 Days</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Present
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Absent
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Attendance Rate
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Trend
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : weeklyStats.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                    No attendance records found
                  </td>
                </tr>
              ) : (
                weeklyStats.map((stat, index) => {
                  const prevRate = index < weeklyStats.length - 1 ? weeklyStats[index + 1].attendance_rate : stat.attendance_rate
                  const trend = stat.attendance_rate > prevRate ? 'up' : stat.attendance_rate < prevRate ? 'down' : 'same'

                  return (
                    <tr key={stat.date} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {new Date(stat.date).toLocaleDateString('en-US', {
                          weekday: 'short',
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric'
                        })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-green-600 font-semibold">
                        {stat.present}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-red-600 font-semibold">
                        {stat.absent}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-900 font-semibold">
                        {stat.total}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                          stat.attendance_rate >= 80 ? 'bg-green-100 text-green-800' :
                          stat.attendance_rate >= 60 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {stat.attendance_rate}%
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                        {trend === 'up' && <span className="text-green-600">↑</span>}
                        {trend === 'down' && <span className="text-red-600">↓</span>}
                        {trend === 'same' && <span className="text-gray-400">→</span>}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
      )}

      {/* Person History */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            {user?.role === 'person' ? 'My Attendance History' : 'Individual History'}
          </h2>
          {user?.role !== 'person' && (
            <select
              value={selectedPerson || ''}
              onChange={(e) => handlePersonSelect(e.target.value)}
              className="w-full md:w-96 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Select a person...</option>
              {persons.map(person => (
                <option key={person.person_id} value={person.person_id}>
                  {person.name} ({person.person_id})
                </option>
              ))}
            </select>
          )}
        </div>

        {selectedPerson && (
          <div className="p-6">
            {personHistory.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No attendance records found for this person</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {personHistory.map(record => (
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
                    {record.is_exam_period === 1 && (
                      <span className="inline-block px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">
                        Exam Period
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
