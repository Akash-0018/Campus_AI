import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { LogOut, Menu, X } from 'lucide-react'
import { useState } from 'react'

export default function Layout() {
  const { logout, role } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const renderNavigation = () => {
    // Layout is only used for admin in 2-user model
    if (role === 'admin') {
      return (
        <nav className="flex flex-col gap-2">
          <NavLink to="/admin/dashboard" label="Dashboard" />
          <NavLink to="/admin/users" label="Users" />
        </nav>
      )
    }
    return null
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <aside className="hidden md:flex w-64 bg-white shadow-lg flex-col">
        <div className="p-6 border-b">
          <h1 className="text-2xl font-bold text-blue-600">Campus AI</h1>
        </div>
        <div className="flex-1 p-6 overflow-y-auto">
          {renderNavigation()}
        </div>
        <div className="p-6 border-t">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-gray-700 hover:text-red-600 w-full font-medium"
          >
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Header */}
        <div className="md:hidden bg-white shadow">
          <div className="flex items-center justify-between p-4">
            <h1 className="text-xl font-bold text-blue-600">Campus AI</h1>
            <button onClick={() => setMenuOpen(!menuOpen)}>
              {menuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
          {menuOpen && (
            <div className="px-4 py-2 border-t bg-gray-50">
              {renderNavigation()}
            </div>
          )}
        </div>

        {/* Page Content */}
        <div className="flex-1 overflow-auto p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

function NavLink({ to, label }: { to: string; label: string }) {
  return (
    <a
      href={to}
      className="text-gray-700 hover:text-blue-600 hover:bg-blue-50 px-4 py-2 rounded-md font-medium transition-colors block"
    >
      {label}
    </a>
  )
}
