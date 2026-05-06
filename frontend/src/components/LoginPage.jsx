import { useState } from 'react'
import { API } from '../api'

export default function LoginPage({ onLogin }) {
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (field, value) => setForm(f => ({ ...f, [field]: value }))

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
      if (!res.ok) {
        setError(data.detail || 'Login failed')
        return
      }
      localStorage.setItem('jwt_token', data.access_token)
      onLogin()
    } catch {
      setError('Could not reach the server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white border border-gray-200 rounded-xl p-8 w-full max-w-sm">
        <div className="mb-6">
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
            <span className="text-white text-sm font-bold">CRM</span>
          </div>
          <h1 className="text-lg font-semibold text-gray-900">Sign in</h1>
          <p className="text-sm text-gray-500 mt-1">AI-CRM — HCP Interaction Logger</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="you@example.com"
              value={form.email}
              onChange={e => set('email', e.target.value)}
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="••••••••"
              value={form.password}
              onChange={e => set('password', e.target.value)}
              required
            />
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 rounded-lg text-sm transition-colors"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
