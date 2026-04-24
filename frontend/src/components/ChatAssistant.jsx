import { useState, useRef, useEffect } from 'react'

const API = 'http://localhost:8000'

const HINTS = [
  'Met Dr. Patel, discussed Metformin',
  'What should I do next after visiting Dr. Roy?',
  'Summarize: Dr. Sharma was interested in the diabetes drug...',
  'Update ID 3: add that samples were requested',
]

export default function ChatAssistant({ onSuccess }) {
  const [messages, setMessages] = useState([
    {
      role: 'agent',
      text: "Hi! I can log interactions, suggest next steps, summarize notes, or extract details from text. Type a message or try one of the hints below.",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send(text) {
    text = (text || input).trim()
    if (!text || loading) return
    setInput('')
    setMessages(m => [...m, { role: 'user', text }])
    setLoading(true)
    try {
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const data = await res.json()
      const reply = res.ok ? data.response : (data.detail || 'Something went wrong.')
      setMessages(m => [...m, { role: 'agent', text: reply }])
      if (reply.toLowerCase().includes('logged') || reply.toLowerCase().includes('updated')) {
        onSuccess()
      }
    } catch {
      setMessages(m => [...m, { role: 'agent', text: 'Could not reach the server. Is the backend running?' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 flex flex-col" style={{ height: '620px' }}>
      <div className="px-6 py-4 border-b border-gray-100 flex-shrink-0">
        <h2 className="text-base font-semibold text-gray-900">AI Chat Assistant</h2>
        <p className="text-xs text-gray-500 mt-0.5">Powered by LangGraph + Groq</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 min-h-0">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[82%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-sm'
                  : 'bg-gray-100 text-gray-800 rounded-bl-sm'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 px-4 py-2.5 rounded-2xl rounded-bl-sm">
              <span className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Hint chips */}
      <div className="px-4 pb-2 flex-shrink-0">
        <div className="flex gap-1.5 flex-wrap">
          {HINTS.map((h, i) => (
            <button
              key={i}
              onClick={() => send(h)}
              disabled={loading}
              className="text-xs bg-gray-50 border border-gray-200 text-gray-500 px-2.5 py-1 rounded-full hover:border-blue-300 hover:text-blue-600 transition-colors disabled:opacity-50"
            >
              {h.length > 30 ? h.slice(0, 30) + '…' : h}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="px-4 pb-4 flex-shrink-0">
        <div className="flex gap-2">
          <input
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Type a message..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            disabled={loading}
          />
          <button
            onClick={() => send()}
            disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
