import { useState } from 'react'

export default function ApiKeySetup({ onSaved }) {
  const [key, setKey] = useState('')
  const [error, setError] = useState('')

  function save(e) {
    e.preventDefault()
    const trimmed = key.trim()
    if (!trimmed) { setError('API key cannot be empty'); return }
    localStorage.setItem('api_key', trimmed)
    onSaved()
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white border border-gray-200 rounded-xl p-8 w-full max-w-md">
        <div className="mb-6">
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
            <span className="text-white text-sm font-bold">CRM</span>
          </div>
          <h1 className="text-lg font-semibold text-gray-900">Enter your API key</h1>
          <p className="text-sm text-gray-500 mt-1">
            Generate one with <code className="bg-gray-100 px-1 rounded text-xs">python create_user.py</code>
          </p>
        </div>

        <form onSubmit={save} className="flex flex-col gap-4">
          <input
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Paste your API key..."
            value={key}
            onChange={e => { setKey(e.target.value); setError('') }}
            autoFocus
          />
          {error && <p className="text-xs text-red-500">{error}</p>}
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg text-sm transition-colors"
          >
            Save &amp; Continue
          </button>
        </form>
      </div>
    </div>
  )
}
