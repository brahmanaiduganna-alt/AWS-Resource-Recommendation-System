import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api, { errorMessage } from '../api'
import ProjectTabs from '../components/ProjectTabs.jsx'

const money = (n) => (n == null ? '-' : '$' + Number(n).toFixed(2))
const BUSY = ['creating', 'deleting']
const COLOR = {
  creating: 'text-amber-700',
  deleting: 'text-amber-700',
  deployed: 'text-green-700',
  failed: 'text-red-700',
  delete_failed: 'text-red-700',
  deleted: 'text-slate-600',
}

export default function Deployment() {
  const { projectId } = useParams()
  const [data, setData] = useState(null)
  const [deployText, setDeployText] = useState('')
  const [deleteName, setDeleteName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const res = await api.get(`/projects/${projectId}/deployment`)
      setData(res.data)
    } catch (err) {
      setError(errorMessage(err))
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  const run = data?.run
  useEffect(() => {
    if (!run || !BUSY.includes(run.status)) return
    const t = setInterval(load, 8000)
    return () => clearInterval(t)
  }, [run, load])

  const act = async (path, body, after) => {
    setBusy(true)
    setError('')
    try {
      await api.post(`/projects/${projectId}/${path}`, body)
      after()
      await load()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (!data) return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-800">Deploy</h1>
      <ProjectTabs projectId={projectId} />
      {error ? <p className="text-red-600 text-sm">{error}</p> : <p className="text-slate-500">Loading...</p>}
    </div>
  )

  const canDeploy = !run || run.status === 'deleted'
  const canDelete = run && !['deleted', 'deleting'].includes(run.status)
  const a = data.approval

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-800">Deploy to AWS</h1>
      <ProjectTabs projectId={projectId} />
      {error && <p className="text-red-600 text-sm">{error}</p>}

      {!data.enabled && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Deployment is switched off (safety). To enable it, set DEPLOY_ENABLED=true in backend/.env and restart the server.
        </div>
      )}

      {canDeploy && (
        <div className="bg-white rounded-xl shadow p-6 space-y-3">
          {!a && <p className="text-slate-600 text-sm">No approval yet. Approve an option on the Approval tab first.</p>}
          {a && (
            <>
              <p className="text-sm text-slate-700">
                Approved: <b>{a.option_label}</b> ({a.compute}) in {a.region}. Estimated <b>{money(a.monthly_usd)}</b> per month.
                Safety cap: {money(data.cost_cap)} per month.
              </p>
              <p className="text-sm text-red-700">
                Deploying creates real, billable AWS resources. You pay until you delete the stack.
              </p>
              <input
                value={deployText}
                onChange={(e) => setDeployText(e.target.value)}
                placeholder="Type DEPLOY"
                className="w-full rounded-lg border border-slate-300 px-3 py-2"
              />
              <button
                disabled={busy || !data.enabled}
                onClick={() => act('deploy', { confirm_text: deployText }, () => setDeployText(''))}
                className="rounded-lg bg-indigo-600 text-white px-4 py-2 hover:bg-indigo-500 disabled:opacity-50"
              >
                {busy ? 'Working...' : 'Deploy'}
              </button>
            </>
          )}
        </div>
      )}

      {run && (
        <div className="bg-white rounded-xl shadow p-6 space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-semibold text-slate-800">Stack {run.stack_name}</h2>
            <span className={'font-semibold ' + (COLOR[run.status] || '')}>{run.status}</span>
            <span className="text-slate-500">({run.aws_status})</span>
          </div>
          <p className="text-slate-600">{run.option_label}: {run.compute} · {run.region} · {money(run.monthly_usd)} per month estimated</p>
          {BUSY.includes(run.status) && <p className="text-amber-700">Working. This page refreshes by itself. Load balancers and databases can take 10 to 20 minutes.</p>}
          {run.reason && <p className="text-red-600">{run.reason}</p>}
          {run.outputs.length > 0 && (
            <div>
              <h3 className="font-medium text-slate-800">Outputs</h3>
              <ul className="list-disc ml-5 text-slate-700 break-all">
                {run.outputs.map((o) => (
                  <li key={o.key}>
                    {o.key}: {o.value.startsWith('http') ? <a className="text-indigo-600 underline" href={o.value} target="_blank" rel="noreferrer">{o.value}</a> : o.value}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {data.events.length > 0 && (
            <details open>
              <summary className="cursor-pointer font-medium text-slate-800">Latest events</summary>
              <div className="overflow-x-auto mt-2">
                <table className="w-full text-xs text-left">
                  <thead><tr className="border-b"><th className="py-1 pr-3">Time</th><th className="pr-3">Resource</th><th className="pr-3">Status</th><th>Reason</th></tr></thead>
                  <tbody>
                    {data.events.map((e, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-1 pr-3 whitespace-nowrap">{new Date(e.time).toLocaleTimeString()}</td>
                        <td className="pr-3">{e.resource}</td>
                        <td className="pr-3">{e.status}</td>
                        <td className="text-slate-500">{e.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}
        </div>
      )}

      {canDelete && (
        <div className="bg-white rounded-xl shadow p-6 space-y-3 border border-red-200">
          <h2 className="text-lg font-semibold text-red-700">Delete AWS resources</h2>
          <p className="text-sm text-slate-600">Removes the whole stack and everything in it, including the database and stored data. This cannot be undone.</p>
          <input
            value={deleteName}
            onChange={(e) => setDeleteName(e.target.value)}
            placeholder={`Type the project name: ${data.project_name}`}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
          />
          <button
            disabled={busy}
            onClick={() => act('deployment/delete', { confirm_name: deleteName }, () => setDeleteName(''))}
            className="rounded-lg bg-red-600 text-white px-4 py-2 hover:bg-red-500 disabled:opacity-50"
          >
            Delete stack
          </button>
        </div>
      )}
    </div>
  )
}
