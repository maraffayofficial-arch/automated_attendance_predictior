import { useState, useRef } from 'react'
import { X, Upload, Download, CheckCircle, AlertCircle } from 'lucide-react'
import client from '../api/client'

export default function ImportCSVModal({ type, onClose, onSuccess }) {
  // type: 'persons' | 'attendance'
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const inputRef = useRef()

  const templates = {
    persons: {
      headers: 'person_id,name,type,department,email',
      example: 'EMP-0001,John Doe,employee,Engineering,john@example.com\nSTU-0001,Jane Smith,student,CS,jane@example.com',
      filename: 'persons_template.csv',
    },
    attendance: {
      headers: 'person_id,date,attendance_binary,is_exam_period',
      example: 'EMP-0001,2026-01-15,1,0\nEMP-0001,2026-01-16,0,1',
      filename: 'attendance_template.csv',
    },
  }

  const downloadTemplate = () => {
    const t = templates[type]
    const content = `${t.headers}\n${t.example}`
    const blob = new Blob([content], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = t.filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) { setError('Please select a CSV file'); return }
    setError('')
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const endpoint = type === 'persons' ? '/persons/import' : '/attendance/bulk'
      const res = await client.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(res.data)
      onSuccess?.()
    } catch (err) {
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timed out. Try a smaller file or check that the backend is running.')
      } else {
        setError(err.response?.data?.error || err.message || 'Import failed')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 className="font-semibold text-slate-800">
            Import {type === 'persons' ? 'Persons' : 'Attendance Records'} from CSV
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={20} />
          </button>
        </div>

        <div className="px-6 py-5">
          {!result ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-2.5 text-sm flex items-center gap-2">
                  <AlertCircle size={16} /> {error}
                </div>
              )}

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-700">CSV File</label>
                  <button
                    type="button"
                    onClick={downloadTemplate}
                    className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
                  >
                    <Download size={13} /> Download template
                  </button>
                </div>
                <div
                  className="border-2 border-dashed border-slate-300 rounded-xl p-6 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
                  onClick={() => inputRef.current?.click()}
                >
                  <Upload className="mx-auto text-slate-400 mb-2" size={24} />
                  {file ? (
                    <p className="text-sm text-slate-700 font-medium">{file.name}</p>
                  ) : (
                    <p className="text-sm text-slate-500">Click to select CSV file</p>
                  )}
                  <input
                    ref={inputRef}
                    type="file"
                    accept=".csv"
                    onChange={(e) => setFile(e.target.files[0])}
                    className="hidden"
                  />
                </div>
              </div>

              <div className="bg-blue-50 rounded-lg p-3 text-xs text-blue-700">
                <p className="font-semibold mb-1">Expected columns:</p>
                <code className="font-mono">{templates[type].headers}</code>
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg hover:bg-slate-50 font-medium text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !file}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white py-2 rounded-lg font-medium text-sm transition-colors"
                >
                  {loading ? 'Importing...' : 'Import'}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl p-4">
                <CheckCircle className="text-green-500 flex-shrink-0" size={24} />
                <div>
                  <p className="font-semibold text-green-800">Import complete</p>
                  <p className="text-sm text-green-700">
                    {result.inserted} inserted · {result.skipped} skipped (duplicates)
                  </p>
                </div>
              </div>
              {result.errors?.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <p className="text-sm font-semibold text-red-700 mb-2">{result.errors.length} errors:</p>
                  <ul className="text-xs text-red-600 space-y-1 max-h-32 overflow-y-auto">
                    {result.errors.map((e, i) => <li key={i}>{e}</li>)}
                  </ul>
                </div>
              )}
              <button
                onClick={onClose}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-medium text-sm"
              >
                Done
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
