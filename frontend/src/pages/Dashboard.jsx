import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../api'
import { useAuth } from '../context/AuthContext.jsx'

const STATUS = {
  draft: 'Needs requirements',
  requirements_saved: 'Requirements saved',
  recommended: 'Recommendation ready',
}

export default function Dashboard() {
  const { user } = useAuth()
  const [projects, setProjects] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get('/projects')
      .then((res) => setProjects(res.data.projects))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  const remove = async (id) => {
    if (!window.confirm('Delete this project and its data?')) return
    try {
      await api.delete(`/projects/${id}`)
      setProjects(projects.filter((p) => p.id !== id))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-800">Welcome, {user?.name}</h1>
        <Link to="/categories" className="rounded-lg bg-indigo-600 text-white px-4 py-2 hover:bg-indigo-500">
          New project
        </Link>
      </div>
      {error && <p className="text-red-600 text-sm">{error}</p>}

      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-3">Project history</h2>
        {loading && <p className="text-slate-400">Loading...</p>}
        {!loading && projects.length === 0 && (
          <p className="text-slate-500">No projects yet. Click "New project" to start.</p>
        )}
        <ul className="divide-y">
          {projects.map((p) => (
            <li key={p.id} className="py-3 flex items-start justify-between gap-4">
              <div>
                <p className="font-medium text-slate-800">{p.name}</p>
                <p className="text-sm text-slate-500">
                  {p.category} · {STATUS[p.status] || p.status} · {new Date(p.created_at).toLocaleString()}
                </p>
                {p.description && <p className="text-sm text-slate-600 mt-1">{p.description}</p>}
              </div>
              <div className="flex gap-4 shrink-0">
                <Link to={`/projects/${p.id}/requirements`} className="text-sm text-indigo-600 hover:underline">
                  Requirements
                </Link>
                <Link to={`/projects/${p.id}/recommendation`} className="text-sm text-indigo-600 hover:underline">
                  Recommendation
                </Link>
                <button onClick={() => remove(p.id)} className="text-sm text-red-600 hover:underline">
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
