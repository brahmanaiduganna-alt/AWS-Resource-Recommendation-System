import { useEffect, useState } from 'react'
import api, { errorMessage } from '../api'
import { useAuth } from '../context/AuthContext.jsx'
import Field from '../components/Field.jsx'

export default function Dashboard() {
  const { user } = useAuth()
  const [projects, setProjects] = useState([])
  const [categories, setCategories] = useState([])
  const [form, setForm] = useState({ name: '', category: '', description: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [p, c] = await Promise.all([
          api.get('/projects'),
          api.get('/projects/categories'),
        ])
        setProjects(p.data.projects)
        setCategories(c.data.categories)
        setForm((f) => ({ ...f, category: c.data.categories[0] }))
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const create = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const res = await api.post('/projects', form)
      setProjects([res.data.project, ...projects])
      setForm({ ...form, name: '', description: '' })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const remove = async (id) => {
    if (!window.confirm('Delete this project?')) return
    try {
      await api.delete(`/projects/${id}`)
      setProjects(projects.filter((p) => p.id !== id))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Welcome, {user?.name}</h1>
      {error && <p className="text-red-600 text-sm">{error}</p>}

      <form onSubmit={create} className="bg-white rounded-xl shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-800">New project</h2>
        <Field label="Project name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Category</span>
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          >
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <Field label="Description (optional)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <button className="rounded-lg bg-indigo-600 text-white px-4 py-2 hover:bg-indigo-500">
          Create project
        </button>
      </form>

      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-3">Project history</h2>
        {loading && <p className="text-slate-400">Loading...</p>}
        {!loading && projects.length === 0 && (
          <p className="text-slate-500">No projects yet. Create your first one above.</p>
        )}
        <ul className="divide-y">
          {projects.map((p) => (
            <li key={p.id} className="py-3 flex items-start justify-between gap-4">
              <div>
                <p className="font-medium text-slate-800">{p.name}</p>
                <p className="text-sm text-slate-500">
                  {p.category} · {p.status} · {new Date(p.created_at).toLocaleString()}
                </p>
                {p.description && <p className="text-sm text-slate-600 mt-1">{p.description}</p>}
              </div>
              <button onClick={() => remove(p.id)} className="text-sm text-red-600 hover:underline">
                Delete
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
