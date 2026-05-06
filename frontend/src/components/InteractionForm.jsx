import { useState } from 'react'
import { API, getJwtHeaders, apiFetch } from '../api'

const SENTIMENT_STYLE = {
  Positive: { idle: 'border-green-300 bg-green-50 text-green-700', active: 'border-green-500 bg-green-500 text-white' },
  Neutral:  { idle: 'border-gray-300 bg-gray-50 text-gray-600',   active: 'border-gray-500 bg-gray-500 text-white'  },
  Negative: { idle: 'border-red-300 bg-red-50 text-red-700',      active: 'border-red-500 bg-red-500 text-white'    },
}

const EMPTY = {
  doctor_name: '', interaction_type: 'Meeting', date_time: '',
  attendees: '', notes: '', products_discussed: '', sentiment: 'Neutral', follow_up: '',
}

export default function InteractionForm({ onSuccess }) {
  const [form, setForm] = useState(EMPTY)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState(null)

  const set = (field, value) => setForm(f => ({ ...f, [field]: value }))

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.doctor_name.trim()) return
    setLoading(true)
    setStatus(null)
    try {
      const res = await apiFetch(`${API}/log-structured-interaction`, {
        method: 'POST',
        headers: getJwtHeaders(),
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed')
      setStatus({ ok: true, text: `Logged successfully — ID: ${data.id}` })
      setForm(EMPTY)
      onSuccess()
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setLoading(false)
    }
  }

  const field = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex flex-col">
      <div className="mb-5">
        <h2 className="text-base font-semibold text-gray-900">Log Interaction</h2>
        <p className="text-xs text-gray-500 mt-0.5">Structured form — saves directly to database</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4 flex-1">

        {/* HCP Name */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            HCP Name <span className="text-red-500">*</span>
          </label>
          <input
            className={field}
            placeholder="e.g. Dr. Sharma"
            value={form.doctor_name}
            onChange={e => set('doctor_name', e.target.value)}
            required
          />
        </div>

        {/* Interaction Type */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Interaction Type</label>
          <div className="flex gap-2">
            {['Meeting', 'Call', 'Visit'].map(t => (
              <button
                key={t} type="button"
                onClick={() => set('interaction_type', t)}
                className={`flex-1 py-1.5 text-sm rounded-lg border font-medium transition-colors ${
                  form.interaction_type === t
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Date & Time + Attendees */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Date & Time</label>
            <input
              type="datetime-local"
              className={field}
              value={form.date_time}
              onChange={e => set('date_time', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Attendees</label>
            <input
              className={field}
              placeholder="e.g. Sales Rep"
              value={form.attendees}
              onChange={e => set('attendees', e.target.value)}
            />
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Discussion Notes</label>
          <textarea
            className={`${field} resize-none`}
            rows={3}
            placeholder="What was discussed during this interaction..."
            value={form.notes}
            onChange={e => set('notes', e.target.value)}
          />
        </div>

        {/* Products + Sentiment */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Products Discussed</label>
          <input
            className={field}
            placeholder="e.g. Metformin, Insulin Glargine"
            value={form.products_discussed}
            onChange={e => set('products_discussed', e.target.value)}
          />
        </div>

        {/* Sentiment */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Sentiment</label>
          <div className="flex gap-2">
            {['Positive', 'Neutral', 'Negative'].map(s => (
              <button
                key={s} type="button"
                onClick={() => set('sentiment', s)}
                className={`flex-1 py-1.5 text-sm rounded-lg border font-medium transition-colors ${
                  form.sentiment === s ? SENTIMENT_STYLE[s].active : SENTIMENT_STYLE[s].idle
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Follow-up */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Follow-up Actions</label>
          <textarea
            className={`${field} resize-none`}
            rows={2}
            placeholder="e.g. Send product samples by Friday"
            value={form.follow_up}
            onChange={e => set('follow_up', e.target.value)}
          />
        </div>

        {status && (
          <div className={`text-sm px-3 py-2 rounded-lg ${status.ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {status.text}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2.5 rounded-lg text-sm transition-colors mt-auto"
        >
          {loading ? 'Logging...' : 'Log Interaction'}
        </button>
      </form>
    </div>
  )
}
