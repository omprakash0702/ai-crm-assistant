import { useState, useCallback } from 'react'
import InteractionForm from './components/InteractionForm'
import ChatAssistant from './components/ChatAssistant'
import InteractionList from './components/InteractionList'

export default function App() {
  const [refresh, setRefresh] = useState(0)
  const triggerRefresh = useCallback(() => setRefresh(r => r + 1), [])

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-xs font-bold">CRM</span>
          </div>
          <div>
            <h1 className="text-base font-semibold text-gray-900">AI-CRM</h1>
            <p className="text-xs text-gray-500">HCP Interaction Logger</p>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <InteractionForm onSuccess={triggerRefresh} />
          <ChatAssistant onSuccess={triggerRefresh} />
        </div>
        <InteractionList refresh={refresh} />
      </main>
    </div>
  )
}
