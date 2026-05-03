import { useState, useEffect, useCallback } from 'react'
import { Play, Download, RefreshCw, TrendingUp, TrendingDown, Minus, Clock, Upload, Search, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import SummaryCards from '../components/SummaryCards'
import AlertTable from '../components/AlertTable'
import ImportCSVModal from '../components/ImportCSVModal'

const trendIcon = { IMPROVING: TrendingUp, DECLINING: TrendingDown, STABLE: Minus }
const trendColor = { IMPROVING: 'text-green-600', DECLINING: 'text-red-500', STABLE: 'text-blue-500' }

export default function Dashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [importing, setImporting] = useState(false)
  const [showAttendanceImport, setShowAttendanceImport] = useState(false)
  const [filter, setFilter] = useState('ALL')
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [showSearchResults, setShowSearchResults] = useState(false)
  const [personsMap, setPersonsMap] = useState({})

  // Redirect persons to their self-attendance page
  useEffect(() => {
    if (user?.role === 'person') {
      navigate('/attendance/self')
    }
  }, [user, navigate]) // Map of person_id -> person details

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3500)
  }

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await client.get('/predictions/')  // Changed from /alerts/
      setData(res.data)
      setError('')

      // Fetch persons to get names
      const personsRes = await client.get('/persons/')
      const personsData = {}
      personsRes.data.forEach(person => {
        personsData[person.person_id] = person
      })
      setPersonsMap(personsData)
    } catch (err) {
      if (err.response?.status === 404) {
        setData(null)
      } else {
        setError('Failed to load prediction data')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAlerts() }, [fetchAlerts])

  const runPipeline = async () => {
    setRunning(true)
    setError('')
    try {
      const res = await client.post('/predictions/refresh', null, { timeout: 600000 }) // 10 min
      showToast(`Analysis complete: ${res.data.analyzed} persons analyzed`)
      await fetchAlerts()
    } catch (err) {
      if (err.code === 'ECONNABORTED') {
        setError('Analysis is taking longer than 10 minutes. Check the backend terminal for progress.')
      } else {
        const data = err.response?.data
      setError(data?.details ? `${data.error}: ${data.details}` : (data?.error || 'Failed to run analysis'))
      }
    } finally {
      setRunning(false)
    }
  }

  const importReport = async () => {
    setImporting(true)
    try {
      const res = await client.post('/alerts/import')
      showToast('Alert report imported successfully')
      await fetchAlerts()
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to import report')
    } finally {
      setImporting(false)
    }
  }

  const filteredAlerts = data?.alerts?.filter(
    (a) => filter === 'ALL' || a.alert_level === filter
  ) ?? []

  // Search functionality
  const handleSearch = (query) => {
    setSearchQuery(query)

    if (!query.trim() || !data?.alerts) {
      setSearchResults([])
      setShowSearchResults(false)
      return
    }

    const lowerQuery = query.toLowerCase()
    const results = data.alerts.filter(alert => {
      const person = personsMap[alert.person_id]
      const personName = person?.name?.toLowerCase() || ''
      const personId = alert.person_id.toLowerCase()

      return personId.includes(lowerQuery) || personName.includes(lowerQuery)
    })

    setSearchResults(results)
    setShowSearchResults(true)
  }

  const clearSearch = () => {
    setSearchQuery('')
    setSearchResults([])
    setShowSearchResults(false)
  }

  const viewPersonDetail = (personId) => {
    navigate(`/persons/${personId}`)
  }

  const trend = data?.group_trend?.trend ?? 'STABLE'
  const TrendIcon = trendIcon[trend] ?? Minus
  const canEdit = user?.role === 'admin' || user?.role === 'teacher'

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Attendance Intelligence</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {data?.generated_at
              ? `Last updated: ${new Date(data.generated_at).toLocaleString()}`
              : 'No predictions yet - add attendance data'}
          </p>
        </div>
        <div className="flex gap-2">
          {canEdit && (
            <>
              <button
                onClick={() => setShowAttendanceImport(true)}
                disabled={running}
                className="flex items-center gap-2 border border-blue-300 text-blue-600 hover:bg-blue-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Upload size={15} />
                Import Attendance CSV
              </button>
              <button
                onClick={importReport}
                disabled={importing || running}
                className="flex items-center gap-2 border border-slate-300 text-slate-600 hover:bg-slate-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Download size={15} />
                {importing ? 'Importing...' : 'Import Report'}
              </button>
            </>
          )}
          <button
            onClick={runPipeline}
            disabled={running || importing}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-60"
          >
            {running ? <RefreshCw size={15} className="animate-spin" /> : <Play size={15} />}
            {running ? 'Refreshing...' : 'Refresh Predictions'}
          </button>
        </div>
      </div>

      {/* Search Bar */}
      {data && (
        <div className="mb-5 relative">
          <div className="relative max-w-md">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by person ID or name (e.g., STU-001, Alice, Bob)..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full pl-10 pr-10 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            {searchQuery && (
              <button
                onClick={clearSearch}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X size={16} />
              </button>
            )}
          </div>

          {/* Search Results Dropdown */}
          {showSearchResults && (
            <div className="absolute top-full mt-2 w-full max-w-md bg-white rounded-lg shadow-lg border border-slate-200 z-50 max-h-96 overflow-y-auto">
              {searchResults.length > 0 ? (
                <div className="py-2">
                  <div className="px-4 py-2 text-xs text-slate-500 font-medium">
                    Found {searchResults.length} result{searchResults.length !== 1 ? 's' : ''}
                  </div>
                  {searchResults.map((alert) => {
                    const person = personsMap[alert.person_id]
                    return (
                      <button
                        key={alert.person_id}
                        onClick={() => {
                          viewPersonDetail(alert.person_id)
                          clearSearch()
                        }}
                        className="w-full px-4 py-3 hover:bg-slate-50 transition-colors text-left border-t border-slate-100"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-semibold text-slate-800 text-sm">
                                {alert.person_id}
                              </span>
                              {person?.name && (
                                <>
                                  <span className="text-slate-300">•</span>
                                  <span className="text-slate-600 text-sm">
                                    {person.name}
                                  </span>
                                </>
                              )}
                            </div>
                            <div className="text-xs text-slate-500 mt-0.5">
                              Risk: {Math.round(alert.combined_risk_score * 100)}% •
                              Next 7 days: {alert.model_details?.xgboost?.predicted_absences_7d || 0} absences
                            </div>
                          </div>
                          <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                            alert.alert_level === 'CRITICAL' ? 'bg-red-100 text-red-700' :
                            alert.alert_level === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                            alert.alert_level === 'MEDIUM' ? 'bg-amber-100 text-amber-700' :
                            'bg-green-100 text-green-700'
                          }`}>
                            {alert.alert_level}
                          </span>
                        </div>
                      </button>
                    )
                  })}
                </div>
              ) : (
                <div className="px-4 py-8 text-center text-slate-400 text-sm">
                  No persons found matching "{searchQuery}"
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed top-5 right-5 bg-green-600 text-white px-5 py-3 rounded-xl shadow-lg text-sm font-medium z-50">
          {toast}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-5 py-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="spinner" />
        </div>
      ) : !data ? (
        /* Empty state */
        <div className="bg-white rounded-2xl shadow-sm p-16 text-center">
          <Clock className="mx-auto text-blue-300 mb-4" size={56} />
          <h2 className="text-xl font-semibold text-slate-700 mb-2">No predictions yet</h2>
          <p className="text-slate-500 text-sm mb-6 max-w-md mx-auto">
            Predictions are generated automatically when you record attendance. Import attendance data or record daily attendance to see predictions.
          </p>
          <div className="flex flex-col items-center gap-3">
            <div className="flex gap-3">
              {canEdit && (
                <button
                  onClick={() => setShowAttendanceImport(true)}
                  className="flex items-center gap-2 border border-blue-300 text-blue-600 hover:bg-blue-50 px-5 py-2 rounded-lg text-sm font-medium"
                >
                  <Upload size={15} /> Import Attendance CSV
                </button>
              )}
              <button onClick={runPipeline} disabled={running} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-semibold flex items-center gap-2">
                {running ? <RefreshCw size={15} className="animate-spin" /> : <Play size={15} />}
                {running ? 'Refreshing...' : 'Refresh Predictions'}
              </button>
            </div>
            {canEdit && (
              <button onClick={importReport} className="text-slate-400 hover:text-slate-600 text-xs">
                Or import an existing alert_report.json
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Summary cards */}
          <SummaryCards
            summary={data.summary}
            activeFilter={filter}
            onFilterChange={setFilter}
          />

          {/* Group trend */}
          <div className="bg-white rounded-xl shadow-sm p-5 flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500 font-medium mb-1">Group Attendance Trend (Prophet)</p>
              <div className="flex items-center gap-3">
                <div className={`flex items-center gap-1.5 font-bold text-lg ${trendColor[trend]}`}>
                  <TrendIcon size={22} />
                  {trend}
                </div>
                <span className="text-slate-300">|</span>
                <span className="text-slate-600 text-sm">
                  Current: <strong>{((data.group_trend?.current_rate ?? 0) * 100).toFixed(1)}%</strong>
                </span>
                <span className="text-slate-300">→</span>
                <span className="text-slate-600 text-sm">
                  Forecast: <strong>{((data.group_trend?.forecast_rate ?? 0) * 100).toFixed(1)}%</strong>
                </span>
              </div>
            </div>
            <div className="text-right text-sm text-slate-500">
              <p>{data.summary?.total_persons ?? 0} persons total</p>
            </div>
          </div>

          {/* Filter tabs */}
          <div className="flex items-center gap-2">
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((lvl) => {
              const count =
                lvl === 'ALL'
                  ? data.alerts?.length ?? 0
                  : data.alerts?.filter((a) => a.alert_level === lvl).length ?? 0
              return (
                <button
                  key={lvl}
                  onClick={() => setFilter(lvl)}
                  className={`px-4 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                    filter === lvl
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'border-slate-200 text-slate-600 hover:border-blue-300 hover:text-blue-600'
                  }`}
                >
                  {lvl} ({count})
                </button>
              )
            })}
          </div>

          {/* Alert table */}
          <AlertTable alerts={filteredAlerts} />
        </div>
      )}

      {showAttendanceImport && (
        <ImportCSVModal
          type="attendance"
          onClose={() => setShowAttendanceImport(false)}
          onSuccess={() => showToast('Attendance records imported — click Run Analysis to generate predictions')}
        />
      )}
    </div>
  )
}
