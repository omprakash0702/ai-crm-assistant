import { useEffect, useState } from 'react'
import { API, getJwtHeaders, apiFetch } from '../api'

function formalName(name) {
  if (!name) return name
  const clean = name.replace(/^dr\.?\s*/i, '').trim()
  if (!clean) return name
  return 'Dr. ' + clean.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ')
}

function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

const SENTIMENT_COLOR = {
  Positive: 'text-green-600 bg-green-50',
  Neutral:  'text-gray-600 bg-gray-100',
  Negative: 'text-red-600 bg-red-50',
}

const TYPE_COLOR = {
  Call:    'text-blue-600 bg-blue-50',
  Visit:   'text-purple-600 bg-purple-50',
  Meeting: 'text-amber-600 bg-amber-50',
}

function DoctorModal({ name, onClose }) {
  const [timeline, setTimeline] = useState(null)
  const [formatted, setFormatted] = useState([])
  const [fmtLoading, setFmtLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch(`${API}/doctor/${encodeURIComponent(name)}/timeline`, { headers: getJwtHeaders() })
      .then(r => r.json())
      .then(data => {
        const rows = Array.isArray(data) ? data : []
        setTimeline(rows)
        if (rows.length === 0) return
        setFmtLoading(true)
        apiFetch(`${API}/format-notes`, {
          method: 'POST',
          headers: getJwtHeaders(),
          body: JSON.stringify({
            notes: rows.map(r => r.notes || ''),
            types: rows.map(r => r.interaction_type || ''),
          }),
        })
          .then(r => r.json())
          .then(d => setFormatted(d.formatted || []))
          .catch(() => setFormatted([]))
          .finally(() => setFmtLoading(false))
      })
      .catch(() => setError('Could not load interactions.'))
  }, [name])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-xl mx-4 max-h-[80vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h3 className="text-base font-semibold text-gray-900">{formalName(name)}</h3>
            <p className="text-xs text-gray-400 mt-0.5">All interactions</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-6 py-4 space-y-3">
          {error && <p className="text-sm text-red-500">{error}</p>}
          {!error && !timeline && <p className="text-sm text-gray-400">Loading...</p>}
          {timeline && timeline.length === 0 && (
            <p className="text-sm text-gray-400">No interactions found.</p>
          )}
          {timeline && timeline.map((item, i) => {
            const fmtNote = formatted[i]
            const hasNote = fmtNote && fmtNote !== '—'
            return (
              <div key={item.id ?? i} className="border border-gray-100 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  {item.interaction_type && (
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${TYPE_COLOR[item.interaction_type] ?? 'text-gray-600 bg-gray-100'}`}>
                      {item.interaction_type}
                    </span>
                  )}
                  {item.sentiment && (
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SENTIMENT_COLOR[item.sentiment] ?? 'text-gray-600 bg-gray-100'}`}>
                      {item.sentiment}
                    </span>
                  )}
                  <span className="text-xs text-gray-400 ml-auto">{formatDate(item.date_time)}</span>
                </div>
                {fmtLoading ? (
                  <p className="text-xs text-gray-400 italic">Formatting...</p>
                ) : hasNote ? (
                  <p className="text-sm text-gray-700 leading-relaxed">{fmtNote}</p>
                ) : null}
                {item.products_discussed && (
                  <p className="text-xs text-gray-500 mt-1.5">
                    <span className="font-medium">Products:</span> {item.products_discussed}
                  </p>
                )}
                {item.follow_up && (
                  <p className="text-xs text-gray-500 mt-1">
                    <span className="font-medium">Follow-up:</span> {item.follow_up}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [topDoctors, setTopDoctors] = useState([])
  const [error, setError] = useState(null)
  const [selectedDoctor, setSelectedDoctor] = useState(null)

  useEffect(() => {
    Promise.all([
      apiFetch(`${API}/metrics/summary`, { headers: getJwtHeaders() }).then(r => r.json()),
      apiFetch(`${API}/metrics/top-doctors`, { headers: getJwtHeaders() }).then(r => r.json()),
    ])
      .then(([s, t]) => {
        setSummary(s)
        setTopDoctors(t)
      })
      .catch(err => setError(err.message))
  }, [])

  if (error) return <p className="text-sm text-red-500">Failed to load dashboard: {error}</p>
  if (!summary) return <p className="text-sm text-gray-400">Loading dashboard...</p>

  return (
    <section>
      <h2 className="text-base font-semibold text-gray-900 mb-4">Dashboard</h2>

      <div className="flex gap-6 mb-6">
        <div className="border border-gray-200 rounded-lg px-5 py-4 bg-white">
          <p className="text-xs text-gray-500 mb-1">Total Interactions</p>
          <p className="text-2xl font-semibold text-gray-900">{summary.total_interactions}</p>
        </div>
        <div className="border border-gray-200 rounded-lg px-5 py-4 bg-white">
          <p className="text-xs text-gray-500 mb-1">Total Doctors</p>
          <p className="text-2xl font-semibold text-gray-900">{summary.total_doctors}</p>
        </div>
        <div className="border border-gray-200 rounded-lg px-5 py-4 bg-white">
          <p className="text-xs text-gray-500 mb-1">Avg per Doctor</p>
          <p className="text-2xl font-semibold text-gray-900">{summary.avg_interactions_per_doctor}</p>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg">
        <p className="text-sm font-medium text-gray-700 px-4 py-3 border-b border-gray-100">Top Doctors</p>
        {topDoctors.length === 0 ? (
          <p className="text-sm text-gray-400 px-4 py-4">No data yet.</p>
        ) : (
          <ul>
            {topDoctors.map((d, i) => (
              <li key={d.name} className="flex items-center justify-between px-4 py-2.5 border-b border-gray-50 last:border-0">
                <button
                  onClick={() => setSelectedDoctor(d.name)}
                  className="text-sm text-blue-600 hover:text-blue-800 hover:underline text-left"
                >
                  {i + 1}. {formalName(d.name)}
                </button>
                <span className="text-xs text-gray-500">{d.interaction_count} interactions</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {selectedDoctor && (
        <DoctorModal name={selectedDoctor} onClose={() => setSelectedDoctor(null)} />
      )}
    </section>
  )
}
