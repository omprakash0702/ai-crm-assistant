import { useState } from 'react'
import { API } from '../api'

const JOB_TITLES = [
  'Medical Sales Representative',
  'Territory Manager',
  'Key Account Manager',
  'Regional Sales Manager',
  'Area Business Manager',
  'Medical Science Liaison',
  'Other',
]

const field =
  'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

function LoginForm({ onLogin }) {
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Login failed'); return }
      localStorage.setItem('jwt_token', data.access_token)
      onLogin()
    } catch {
      setError('Could not reach the server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">Work Email</label>
        <input
          type="email" className={field} placeholder="you@company.com"
          value={form.email} onChange={e => set('email', e.target.value)}
          required autoFocus
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">Password</label>
        <input
          type="password" className={field} placeholder="••••••••"
          value={form.password} onChange={e => set('password', e.target.value)}
          required
        />
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <button
        type="submit" disabled={loading}
        className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 rounded-lg text-sm transition-colors"
      >
        {loading ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  )
}

function SignupForm({ onLogin }) {
  const EMPTY = {
    name: '', email: '', password: '', company: '', job_title: JOB_TITLES[0], territory: '',
  }
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const payload = { ...form, territory: form.territory.trim() || undefined }
      const res = await fetch(`${API}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Registration failed'); return }
      localStorage.setItem('jwt_token', data.access_token)
      onLogin()
    } catch {
      setError('Could not reach the server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {/* Name + Company */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Full Name <span className="text-red-500">*</span>
          </label>
          <input
            className={field} placeholder="Ravi Sharma"
            value={form.name} onChange={e => set('name', e.target.value)}
            required autoFocus
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Company <span className="text-red-500">*</span>
          </label>
          <input
            className={field} placeholder="Pharma Ltd."
            value={form.company} onChange={e => set('company', e.target.value)}
            required
          />
        </div>
      </div>

      {/* Work Email */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Work Email <span className="text-red-500">*</span>
        </label>
        <input
          type="email" className={field} placeholder="ravi@pharma.com"
          value={form.email} onChange={e => set('email', e.target.value)}
          required
        />
      </div>

      {/* Job Title */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Job Title <span className="text-red-500">*</span>
        </label>
        <select
          className={field}
          value={form.job_title}
          onChange={e => set('job_title', e.target.value)}
          required
        >
          {JOB_TITLES.map(t => <option key={t}>{t}</option>)}
        </select>
      </div>

      {/* Territory */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Territory / Region <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <input
          className={field} placeholder="e.g. North Delhi, Maharashtra West"
          value={form.territory} onChange={e => set('territory', e.target.value)}
        />
      </div>

      {/* Password */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Password <span className="text-red-500">*</span>
        </label>
        <input
          type="password" className={field} placeholder="Min. 8 characters"
          value={form.password} onChange={e => set('password', e.target.value)}
          required minLength={8}
        />
      </div>

      {error && <p className="text-xs text-red-500">{error}</p>}

      <button
        type="submit" disabled={loading}
        className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 rounded-lg text-sm transition-colors"
      >
        {loading ? 'Creating account...' : 'Create Account'}
      </button>
    </form>
  )
}

export default function AuthPage({ onLogin }) {
  const [tab, setTab] = useState('login')

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-8">
      <div className="bg-white border border-gray-200 rounded-xl p-8 w-full max-w-md">

        {/* Brand */}
        <div className="mb-6">
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
            <span className="text-white text-sm font-bold">CRM</span>
          </div>
          <h1 className="text-lg font-semibold text-gray-900">AI-CRM</h1>
          <p className="text-sm text-gray-500 mt-0.5">HCP Interaction Logger for Sales Teams</p>
        </div>

        {/* Tabs */}
        <div className="flex rounded-lg border border-gray-200 p-1 mb-6 gap-1">
          {[['login', 'Sign In'], ['signup', 'Create Account']].map(([id, label]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${
                tab === id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === 'login'
          ? <LoginForm onLogin={onLogin} />
          : <SignupForm onLogin={onLogin} />
        }
      </div>
    </div>
  )
}
