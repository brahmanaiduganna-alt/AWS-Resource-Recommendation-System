import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import api, { errorMessage } from '../api'
import ProjectTabs from '../components/ProjectTabs.jsx'

const money = (n) => (n == null ? '-' : '$' + Number(n).toFixed(2))

export default function Approval() {
  const { projectId } = useParams()
  const [params] = useSearchParams()
  const [project, setProject] = useState(null)
  const [rec, setRec] = useState(null)
  const [approval, setApproval] = useState(null)
  const [optionKey, setOptionKey] = useState(params.get('option') || '')
  const [confirm, setConfirm] = useState(false)
  const [typedName, setTypedName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const [r, a] = await Promise.all([
          api.get(`/projects/${projectId}/recommendation`),
          api.get(`/projects/${projectId}/approval`),
        ])
        setProject(r.data.project)
        setRec(r.data.recommendation)
        setApproval(a.data.approval)
        if (r.data.recommendation && !optionKey) setOptionKey(r.data.recommendation.options[0].key)
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const res = await api.post(`/projects/${projectId}/approve`, {
        option_key: optionKey,
        confirm,
        confirm_name: typedName,
      })
      setApproval(res.data.approval)
      setConfirm(false)
      setTypedName('')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <p className="text-slate-500">Loading...</p>
  const chosen = rec?.options.find((o) => o.key === optionKey)

  return (
    <div className="space-y-4 max-w-2xl">
      <h1 className="text-2xl font-bold text-slate-800">Approval</h1>
      <ProjectTabs projectId={projectId} />
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!rec && !error && <p className="text-slate-500">Generate the recommendation first.</p>}

      {approval && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-900">
          Approved: <b>{approval.option_label}</b> ({approval.compute}) at {money(approval.monthly_usd)} per month in {approval.region}
          on {new Date(approval.approved_at).toLocaleString()}. No AWS resources have been created yet.
        </div>
      )}

      {rec && (
        <form onSubmit={submit} className="bg-white rounded-xl shadow p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-800">Choose the option to approve</h2>
          <div className="space-y-2">
            {rec.options.map((o) => (
              <label key={o.key} className="flex items-start gap-3 rounded-lg border p-3 cursor-pointer">
                <input type="radio" name="option" checked={optionKey === o.key} onChange={() => setOptionKey(o.key)} className="mt-1" />
                <span className="text-sm">
                  <b>{o.label}</b>: {o.compute}, {money(o.monthly_usd)} per month
                  {!o.within_budget && <span className="text-red-600"> (over your budget)</span>}
                </span>
              </label>
            ))}
          </div>

          {chosen && (
            <div className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3">
              Would create in {rec.region}: {chosen.compute}; {chosen.storage.service}
              {chosen.uses_load_balancer ? '; an Application Load Balancer' : ''}; a CloudWatch alarm set.
              Estimated {money(chosen.monthly_usd)} per month (reference prices, see assumptions).
            </div>
          )}

          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} className="mt-1" />
            I understand that deploying later will create billable AWS resources.
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Type the project name ({project?.name}) to confirm</span>
            <input value={typedName} onChange={(e) => setTypedName(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
          </label>
          <button disabled={busy} className="rounded-lg bg-indigo-600 text-white px-4 py-2 hover:bg-indigo-500 disabled:opacity-60">
            {busy ? 'Saving...' : 'Approve'}
          </button>
        </form>
      )}
    </div>
  )
}
