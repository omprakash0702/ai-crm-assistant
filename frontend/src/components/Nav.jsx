export default function Nav({ page, setPage, onLogout }) {
  const tabs = [
    { id: 'chat', label: 'Chat' },
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'system', label: 'System' },
  ]

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-0">
      <div className="max-w-7xl mx-auto flex items-center gap-6">
        <div className="flex items-center gap-3 py-4 mr-4">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-white text-xs font-bold">CRM</span>
          </div>
          <div>
            <h1 className="text-base font-semibold text-gray-900 leading-tight">AI-CRM</h1>
            <p className="text-xs text-gray-500 leading-tight">HCP Interaction Logger</p>
          </div>
        </div>

        <nav className="flex gap-1 flex-1">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setPage(t.id)}
              className={`px-4 py-4 text-sm font-medium border-b-2 transition-colors ${
                page === t.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <button
          onClick={onLogout}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors py-4"
        >
          Logout
        </button>
      </div>
    </header>
  )
}
