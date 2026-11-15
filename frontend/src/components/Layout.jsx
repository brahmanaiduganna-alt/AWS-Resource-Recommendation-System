import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const linkClass = ({ isActive }) =>
    'px-3 py-1 rounded-lg ' +
    (isActive ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:text-slate-900')

  return (
    <div className="min-h-screen bg-slate-100">
      <nav className="bg-white shadow">
        <div className="max-w-5xl mx-auto px-4 py-3 flex flex-wrap items-center gap-2">
          <span className="font-bold text-slate-800 mr-4">Cloud Recommender</span>
          <NavLink to="/" end className={linkClass}>Dashboard</NavLink>
          <NavLink to="/categories" className={linkClass}>Categories</NavLink>
          <NavLink to="/deployments" className={linkClass}>History</NavLink>
          <NavLink to="/assistant" className={linkClass}>Assistant</NavLink>
          <NavLink to="/settings" className={linkClass}>Settings</NavLink>
          <NavLink to="/profile" className={linkClass}>Profile</NavLink>
          <span className="ml-auto text-sm text-slate-500">{user?.name}</span>
          <button
            onClick={handleLogout}
            className="px-3 py-1 rounded-lg bg-slate-800 text-white hover:bg-slate-700"
          >
            Logout
          </button>
        </div>
      </nav>
      <main className="max-w-5xl mx-auto p-4">
        <Outlet />
      </main>
    </div>
  )
}
