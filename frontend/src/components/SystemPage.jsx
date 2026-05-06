import { useEffect, useState } from 'react'
import { API, getJwtHeaders, apiFetch } from '../api'

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-5 py-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-semibold text-gray-900">{value ?? '—'}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

function InfoRow({ label, value, mono }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-gray-50 last:border-0">
      <span className="text-sm text-gray-600">{label}</span>
      <span className={`text-sm text-gray-900 ${mono ? 'font-mono text-xs bg-gray-100 px-2 py-0.5 rounded' : 'font-medium'}`}>
        {value}
      </span>
    </div>
  )
}

export default function SystemPage() {
  const [metrics, setMetrics] = useState(null)
  const [summary, setSummary] = useState(null)
  const [queue, setQueue] = useState(null)
  const [status, setStatus] = useState('loading')
  const [apiKeyMasked, setApiKeyMasked] = useState('')

  useEffect(() => {
    const key = localStorage.getItem('api_key') || ''
    setApiKeyMasked(key ? key.slice(0, 8) + '••••••••••••••••' + key.slice(-4) : 'Not set')

    Promise.all([
      apiFetch(`${API}/metrics/system`, { headers: getJwtHeaders() }).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      }),
      apiFetch(`${API}/metrics/summary`, { headers: getJwtHeaders() }).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      }),
      apiFetch(`${API}/metrics/queue`, { headers: getJwtHeaders() }).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      }),
    ])
      .then(([sys, sum, q]) => { setMetrics(sys); setSummary(sum); setQueue(q); setStatus('ok') })
      .catch(() => setStatus('error'))
  }, [])

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-base font-semibold text-gray-900">Know Your System</h2>
        <p className="text-xs text-gray-500 mt-0.5">Live stats and configuration overview</p>
      </div>

      {status === 'loading' && <p className="text-sm text-gray-400">Loading...</p>}
      {status === 'error' && <p className="text-sm text-red-500">Failed to load metrics. Is the backend running?</p>}

      {status === 'ok' && (
        <>
          {/* CRM Stats */}
          {summary && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard label="Total Interactions" value={summary.total_interactions} />
              <StatCard label="Total Doctors" value={summary.total_doctors} />
              <StatCard label="Avg per Doctor" value={summary.avg_interactions_per_doctor} />
            </div>
          )}

          {/* LLM Stats */}
          <div className="bg-white border border-gray-200 rounded-xl">
            <p className="text-sm font-medium text-gray-700 px-5 py-3 border-b border-gray-100">LLM Usage</p>
            <div className="px-5 py-1">
              <InfoRow label="Total LLM calls" value={metrics.total_llm_calls} />
              <InfoRow label="Avg latency" value={metrics.avg_latency_ms ? `${metrics.avg_latency_ms} ms` : '—'} />
              <InfoRow label="Total cost" value={metrics.total_cost_usd ? `$${metrics.total_cost_usd}` : '$0.000000'} />
              <InfoRow label="Groq calls" value={metrics.model_usage.groq} />
              <InfoRow label="OpenAI calls" value={metrics.model_usage.openai} />
            </div>
          </div>

          {/* Resilience */}
          <div className="bg-white border border-gray-200 rounded-xl">
            <p className="text-sm font-medium text-gray-700 px-5 py-3 border-b border-gray-100">Resilience</p>
            <div className="px-5 py-1">
              <InfoRow
                label="Failures handled via retry"
                value={metrics.retry_count > 0 ? metrics.retry_count : '0 (no retries needed)'}
              />
              <InfoRow
                label="Requests failed (all retries exhausted)"
                value={metrics.failed_requests > 0
                  ? `${metrics.failed_requests} (fallback message returned)`
                  : '0'}
              />
            </div>
            <div className="px-5 pb-3 pt-1">
              <p className="text-xs text-gray-400">
                Each retry represents a transient LLM failure that was automatically re-attempted.
                A failed request means both primary and fallback model were exhausted.
              </p>
            </div>
          </div>

          {/* Cache Stats */}
          <div className="bg-white border border-gray-200 rounded-xl">
            <p className="text-sm font-medium text-gray-700 px-5 py-3 border-b border-gray-100">Cache (Redis)</p>
            <div className="px-5 py-1">
              <InfoRow label="Cache hits" value={metrics.cache_hits} />
              <InfoRow label="Cache misses" value={metrics.cache_misses} />
            </div>
            {/* Hit rate bar */}
            <div className="px-5 pb-3 pt-1">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm text-gray-600">Hit rate</span>
                <span className="text-sm font-semibold text-gray-900">
                  {metrics.cache_hit_rate_percentage ?? 0}%
                </span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div
                  className="h-2 rounded-full transition-all"
                  style={{
                    width: `${metrics.cache_hit_rate_percentage ?? 0}%`,
                    backgroundColor:
                      (metrics.cache_hit_rate_percentage ?? 0) >= 70 ? '#16a34a' :
                      (metrics.cache_hit_rate_percentage ?? 0) >= 40 ? '#d97706' : '#dc2626',
                  }}
                />
              </div>
            </div>
            <div className="px-5 pb-3 border-t border-gray-50 pt-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Est. speed gain</span>
                <span className="text-sm font-medium text-gray-900">
                  {metrics.estimated_speed_gain_ms > 0
                    ? `~${metrics.estimated_speed_gain_ms} ms saved per request`
                    : 'No gain yet'}
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                Based on {metrics.cache_hit_rate_percentage ?? 0}% of requests served from cache (avg LLM call ≈ 1500 ms)
              </p>
            </div>
          </div>
        </>
      )}

      {/* Auth */}
      <div className="bg-white border border-gray-200 rounded-xl">
        <p className="text-sm font-medium text-gray-700 px-5 py-3 border-b border-gray-100">Authentication</p>
        <div className="px-5 py-1">
          <InfoRow label="API Key" value={apiKeyMasked} mono />
          <InfoRow label="Auth Method" value="X-API-Key header" />
          <InfoRow label="Rate Limit" value="60 requests / minute" />
        </div>
      </div>

      {/* Model Routing */}
      <div className="bg-white border border-gray-200 rounded-xl">
        <p className="text-sm font-medium text-gray-700 px-5 py-3 border-b border-gray-100">Model Routing</p>
        <div className="px-5 py-1">
          <InfoRow label="Fast tasks (log, edit, update)" value="Groq — llama-3.1-8b-instant" />
          <InfoRow label="Complex tasks (summarize, next step)" value="OpenAI — gpt-4o-mini" />
          <InfoRow label="Retry policy" value="3 retries, 5s timeout each" />
          <InfoRow label="Fallback" value="Safe error message on all failures" />
        </div>
      </div>

      {/* Infrastructure */}
      <div className="bg-white border border-gray-200 rounded-xl">
        <p className="text-sm font-medium text-gray-700 px-5 py-3 border-b border-gray-100">Infrastructure</p>
        <div className="px-5 py-1">
          <InfoRow label="Database" value="PostgreSQL (psycopg2 pool, 1–10 conns)" />
          <InfoRow label="Cache" value="Redis — summary + doctor history" />
          <InfoRow label="Task Queue" value="RQ + SimpleWorker (Windows)" />
          <InfoRow label="Agent Framework" value="LangGraph + create_react_agent" />
          <InfoRow label="Logging" value="Structured JSON — stdout" />
          <InfoRow
            label="Jobs processed"
            value={queue ? queue.total_jobs_processed : '—'}
          />
          <InfoRow
            label="Jobs pending"
            value={
              queue
                ? queue.pending_jobs === 0
                  ? '0 (queue idle)'
                  : queue.pending_jobs
                : '—'
            }
          />
        </div>
      </div>

      {/* Connection */}
      <div className="bg-white border border-gray-200 rounded-xl">
        <p className="text-sm font-medium text-gray-700 px-5 py-3 border-b border-gray-100">Connection</p>
        <div className="px-5 py-1">
          <InfoRow label="Backend URL" value={API} mono />
          <InfoRow
            label="Status"
            value={status === 'ok' ? 'Connected' : status === 'error' ? 'Unreachable' : 'Checking...'}
          />
        </div>
      </div>
    </section>
  )
}
