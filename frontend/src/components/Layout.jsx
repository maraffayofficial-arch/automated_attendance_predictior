import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { BarChart2, Users, LayoutDashboard, LogOut, Calendar, History, CheckSquare } from 'lucide-react'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // Different navigation items based on role
  const getNavItems = () => {
    if (user?.role === 'person') {
      return [
        { to: '/attendance/self', icon: CheckSquare, label: 'My Attendance' },
        { to: '/attendance/history', icon: History, label: 'My History' },
      ]
    }

    // Admin, teacher, viewer navigation
    return [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/attendance/daily', icon: Calendar, label: 'Daily Attendance' },
      { to: '/attendance/history', icon: History, label: 'Attendance History' },
      { to: '/persons', icon: Users, label: 'Persons' },
    ]
  }

  const navItems = getNavItems()

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-blue-900 flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-blue-800">
          <div className="bg-blue-500 p-2 rounded-lg">
            <BarChart2 className="text-white" size={20} />
          </div>
          <div>
            <p className="text-white font-bold text-sm leading-tight">Attendance</p>
            <p className="text-blue-300 text-xs">Intelligence</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-700 text-white'
                    : 'text-blue-200 hover:bg-blue-800 hover:text-white'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="border-t border-blue-800 p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">
              {user?.username?.[0]?.toUpperCase()}
            </div>
            <div className="overflow-hidden">
              <p className="text-white text-sm font-medium truncate">{user?.username}</p>
              <p className="text-blue-400 text-xs capitalize">{user?.role}</p>
              {user?.department && (
                <p className="text-blue-300 text-xs">{user.department}</p>
              )}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-blue-300 hover:text-white text-sm w-full px-2 py-1.5 rounded hover:bg-blue-800 transition-colors"
          >
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto bg-slate-50">
        <Outlet />
      </main>
    </div>
  )
}
