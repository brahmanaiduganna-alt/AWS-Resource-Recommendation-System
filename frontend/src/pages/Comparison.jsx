import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { errorMessage } from '../api'
import ProjectTabs from '../components/ProjectTabs.jsx'

const money = (n) => (n == null ? '-' : '$' + Number(n).toFixed(2))

export default function Comparison() {
  const { projectId } = useParams()
  const [rec, setRec] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get(`/projects/${projectId}/recommendation`)
      .then((res) => setRec(res.data.recommendation))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) return <p className="text-slate-500">Loading...</p>

  const opts = rec?.options || []
  const cheapest = opts.length ? Math.min(...opts.map((o) => o.monthly_usd)) : null

  const rows = [
    ['Compute', (o) => o.compute],
    ['Instance family', (o) => o.family],
    ['Total vCPU', (o) => o.vcpu_total ?? '-'],
    ['Total RAM (GB)', (o) => o.ram_total ?? '-'],
    ['Storage', (o) => o.storage.service],
    ['Load balancer', (o) => (o.uses_load_balancer ? 'Yes' : 'No')],
    ['Monthly cost', (o) => money(o.monthly_usd)],
    ['Within budget', (o) => (o.within_budget ? 'Yes' : 'No')],
    ['With Savings Plan (illustrative)', (o) => money(o.savings.savings_plan_total)],
    ['With Spot (illustrative)', (o) => money(o.savings.spot_total)],
  ]

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-800">Comparison</h1>
      <ProjectTabs projectId={projectId} />
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!rec && !error && <p className="text-slate-500">Generate the recommendation first.</p>}
      {rec && (
        <div className="bg-white rounded-xl shadow p-6 overflow-x-auto">
          <p className="text-sm text-slate-500 mb-3">
            Budget {money(rec.budget_usd)} per month, region {rec.region}, prices: {rec.price_source}.
          </p>
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b">
                <th className="py-2 pr-4"></th>
                {opts.map((o) => (
                  <th key={o.key} className="py-2 px-3 font-semibold text-slate-800">
                    {o.label}
                    {o.monthly_usd === cheapest && (
                      <span className="ml-2 text-xs rounded-full bg-green-100 text-green-800 px-2 py-0.5">Cheapest</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(([label, fn]) => (
                <tr key={label} className="border-b last:border-0">
                  <td className="py-2 pr-4 text-slate-500">{label}</td>
                  {opts.map((o) => (
                    <td key={o.key} className="py-2 px-3 text-slate-800">{fn(o)}</td>
                  ))}
                </tr>
              ))}
              <tr>
                <td className="py-3 pr-4"></td>
                {opts.map((o) => (
                  <td key={o.key} className="py-3 px-3">
                    <Link
                      to={`/projects/${projectId}/approval?option=${o.key}`}
                      className="rounded-lg bg-indigo-600 text-white px-3 py-1 hover:bg-indigo-500"
                    >
                      Choose
                    </Link>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
