import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import api, { errorMessage } from '../api'
import Field from '../components/Field.jsx'

const EMPTY = {
  users: '',
  cpu_vcpu: '',
  ram_gb: '',
  storage_gb: '',
  traffic_gb_month: '',
  budget_usd_month: '',
  region: 'ap-south-1',
  performance: 'medium',
}

const selectClass = 'mt-1 w-full rounded-lg border border-slate-300 px-3 py-2'

export default function Requirements() {
  const { projectId } = useParams()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const editing = Boolean(projectId)

  const [meta, setMeta] = useState(null)
  const [name, setName] = useState('')
  const [category, setCategory] = useState(params.get('category') || '')
  const [description, setDescription] = useState('')
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const m = await api.get('/meta')
        setMeta(m.data)
        if (!editing && !category) setCategory(m.data.categories[0].name)
        if (editing) {
          const res = await api.get(`/projects/${projectId}/requirements`)
          setName(res.data.project.name)
          setCategory(res.data.project.category)
          setDescription(res.data.project.description || '')
          if (res.data.requirements) setForm({ ...EMPTY, ...res.data.requirements })
        }
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    let createdId = null
    try {
      let id = projectId
      if (!editing) {
        const created = await api.post('/projects', { name, category, description })
        id = created.data.project.id
        createdId = id
      }
      await api.put(`/projects/${id}/requirements`, form)
      navigate(`/projects/${id}/recommendation`)
    } catch (err) {
      if (createdId) {
        try { await api.delete(`/projects/${createdId}`) } catch { /* ignore */ }
      }
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <p className="text-slate-500">Loading...</p>
  if (!meta) return <p className="text-red-600">{error || 'Could not load form data.'}</p>

  return (
    <form onSubmit={submit} className="bg-white rounded-xl shadow p-6 space-y-4 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">
          {editing ? 'Edit requirements' : 'New project requirements'}
        </h1>
        <p className="text-slate-500 text-sm">
          These values are used for the recommendation and cost estimate.
        </p>
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <Field label="Project name" value={name} onChange={(e) => setName(e.target.value)} disabled={editing} required />

      <label className="block">
        <span className="text-sm font-medium text-slate-700">Category</span>
        <select className={selectClass} value={category} onChange={(e) => setCategory(e.target.value)} disabled={editing}>
          {meta.categories.map((c) => (
            <option key={c.name} value={c.name}>{c.name}</option>
          ))}
        </select>
      </label>

      {!editing && (
        <Field label="Description (optional)" value={description} onChange={(e) => setDescription(e.target.value)} />
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Expected users" type="number" min="1" step="1" value={form.users} onChange={set('users')} required />
        <Field label="CPU (vCPUs)" type="number" min="1" step="1" value={form.cpu_vcpu} onChange={set('cpu_vcpu')} required />
        <Field label="RAM (GB)" type="number" min="1" step="1" value={form.ram_gb} onChange={set('ram_gb')} required />
        <Field label="Storage (GB)" type="number" min="1" step="1" value={form.storage_gb} onChange={set('storage_gb')} required />
        <Field label="Data transfer out (GB per month)" type="number" min="0" step="any" value={form.traffic_gb_month} onChange={set('traffic_gb_month')} required />
        <Field label="Monthly budget (USD)" type="number" min="1" step="any" value={form.budget_usd_month} onChange={set('budget_usd_month')} required />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm font-medium text-slate-700">AWS region</span>
          <select className={selectClass} value={form.region} onChange={set('region')}>
            {meta.regions.map((r) => (
              <option key={r.code} value={r.code}>{r.name} - {r.code}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Performance level</span>
          <select className={selectClass} value={form.performance} onChange={set('performance')}>
            {meta.performance_levels.map((p) => (
              <option key={p} value={p}>{p[0].toUpperCase() + p.slice(1)}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex gap-3">
        <button disabled={busy} className="rounded-lg bg-indigo-600 text-white px-4 py-2 hover:bg-indigo-500 disabled:opacity-60">
          {busy ? 'Saving...' : 'Save requirements'}
        </button>
        <Link to="/" className="rounded-lg border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50">
          Cancel
        </Link>
      </div>
    </form>
  )
}
