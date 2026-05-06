import { useState, useCallback, useEffect } from 'react'
import AuthPage from './components/AuthPage'
import Nav from './components/Nav'
import Dashboard from './components/Dashboard'
import InteractionForm from './components/InteractionForm'
import ChatAssistant from './components/ChatAssistant'
import InteractionList from './components/InteractionList'
import SystemPage from './components/SystemPage'

function hasToken() {
  return !!localStorage.getItem('jwt_token')
}

export default function App() {
  const [authed, setAuthed] = useState(hasToken)
  const [page, setPage] = useState('chat')
  const [refresh, setRefresh] = useState(0)
  const triggerRefresh = useCallback(() => setRefresh(r => r + 1), [])

  useEffect(() => {
    const handler = () => setAuthed(false)
    window.addEventListener('auth:logout', handler)
    return () => window.removeEventListener('auth:logout', handler)
  }, [])

  function logout() {
    localStorage.removeItem('jwt_token')
    setAuthed(false)
  }

  if (!authed) {
    return <AuthPage onLogin={() => setAuthed(true)} />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav page={page} setPage={setPage} onLogout={logout} />

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {page === 'chat' && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <InteractionForm onSuccess={triggerRefresh} />
              <ChatAssistant onSuccess={triggerRefresh} />
            </div>
            <InteractionList refresh={refresh} />
          </>
        )}

        {page === 'dashboard' && <Dashboard />}

        {page === 'system' && <SystemPage />}
      </main>
    </div>
  )
}
