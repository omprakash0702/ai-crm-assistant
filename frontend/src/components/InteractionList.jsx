import { useEffect, useState } from 'react'
import { API, getJwtHeaders, apiFetch } from '../api'

const SENTIMENT_BADGE = {
  Positive: 'bg-green-100 text-green-700',
  Neutral:  'bg-gray-100 text-gray-600',
  Negative: 'bg-red-100 text-red-700',
}

const TYPE_BADGE = {
  Meeting: 'bg-blue-100 text-blue-700',
  Call:    'bg-purple-100 text-purple-700',
  Visit:   'bg-orange-100 text-orange-700',
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}

function formalName(name) {
  if (!name) return name
  const clean = name.replace(/^dr\.?\s*/i, '').trim()
  if (!clean) return name
  return 'Dr. ' + clean.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ')
}

export default function InteractionList({ refresh }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    apiFetch(`${API}/interactions`, { headers: getJwtHeaders() })
      .then(r => r.json())
      .then(data => { setRows(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [refresh])

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-900">Recent Interactions</h2>
        <span className="text-xs text-gray-400">{rows.length} records</span>
      </div>

      {loading && (
        <div className="text-sm text-gray-400 text-center py-10">Loading...</div>
      )}
      {error && (
        <div className="text-sm text-red-500 text-center py-10">Error: {error}</div>
      )}
      {!loading && !error && rows.length === 0 && (
        <div className="text-sm text-gray-400 text-center py-10">No interactions logged yet.</div>
      )}
      {!loading && rows.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {rows.map(item => (
            <div key={item.id} className="bg-white rounded-xl border border-gray-200 p-4 flex flex-col gap-2">
              {/* Header */}
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-semibold text-gray-900 text-sm truncate">{formalName(item.doctor_name)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">#{item.id} · {formatDate(item.created_at)}</p>
                </div>
                <div className="flex gap-1.5 flex-shrink-0">
                  {item.interaction_type && (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TYPE_BADGE[item.interaction_type] || 'bg-gray-100 text-gray-600'}`}>
                      {item.interaction_type}
                    </span>
                  )}
                  {item.sentiment && (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SENTIMENT_BADGE[item.sentiment] || 'bg-gray-100 text-gray-600'}`}>
                      {item.sentiment}
                    </span>
                  )}
                </div>
              </div>

              {/* Notes */}
              {item.notes && (
                <p className="text-xs text-gray-600 line-clamp-2">{item.notes}</p>
              )}

              {/* Follow-up */}
              {item.follow_up && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5 mt-auto">
                  <p className="text-xs text-amber-700">
                    <span className="font-medium">Follow-up: </span>{item.follow_up}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
