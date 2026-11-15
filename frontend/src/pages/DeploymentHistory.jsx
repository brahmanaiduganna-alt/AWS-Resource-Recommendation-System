import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../api'

const money = (n) => (n == null ? '-' : '$' + Number(n).toFixed(2))

export default function DeploymentHistory() {
  const [runs, setRuns] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get('/deployments')
      .then((res) => setRuns(res.data.runs))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-800">Deployment history</h1>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {loading && <p className="text-slate-500">Loading...</p>}
      {!loading && runs.length === 0 && <p className="text-slate-500">No deployments yet.</p>}
      {runs.length > 0 && (
        <div className="bg-white rounded-xl shadow p-6 overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b">
                <th className="py-2 pr-4">Project</th><th className="pr-4">Option</th><th className="pr-4">Region</th>
                <th className="pr-4">Est. monthly</th><th className="pr-4">Status</th><th className="pr-4">Started</th><th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-b last:border-0">
                  <td className="py-2 pr-4 text-slate-800">{r.project_name}</td>
                  <td className="pr-4">{r.option_label}</td>
                  <td className="pr-4">{r.region}</td>
                  <td className="pr-4">{money(r.monthly_usd)}</td>
                  <td className="pr-4">{r.status}</td>
                  <td className="pr-4 whitespace-nowrap">{new Date(r.created_at).toLocaleString()}</td>
                  <td><Link className="text-indigo-600 hover:underline" to={`/projects/${r.project_id}/deploy`}>Open</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
