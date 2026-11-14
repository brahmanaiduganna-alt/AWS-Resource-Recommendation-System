import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Bar } from 'react-chartjs-2'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js'
import api, { errorMessage } from '../api'
import ProjectTabs from '../components/ProjectTabs.jsx'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const COMPONENTS = [
  ['ec2', 'EC2', '#4f46e5'],
  ['lambda_api', 'Lambda + API', '#8b5cf6'],
  ['storage', 'Storage', '#10b981'],
  ['database', 'Database', '#f59e0b'],
  ['load_balancer', 'Load balancer', '#ef4444'],
  ['data_transfer', 'Data transfer', '#06b6d4'],
  ['monitoring', 'Monitoring', '#64748b'],
]

const money = (n) => (n == null ? '-' : '$' + Number(n).toFixed(2))

export default function Recommendation() {
  const { projectId } = useParams()
  const [project, setProject] = useState(null)
  const [rec, setRec] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get(`/projects/${projectId}/recommendation`)
      .then((res) => {
        setProject(res.data.project)
        setRec(res.data.recommendation)
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [projectId])

  const generate = async () => {
    setError('')
    setBusy(true)
    try {
      const res = await api.post(`/projects/${projectId}/recommend`)
      setRec(res.data.recommendation)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <p className="text-slate-500">Loading...</p>

  const chartData = rec && {
    labels: rec.options.map((o) => o.label),
    datasets: COMPONENTS.filter(([k]) => rec.options.some((o) => o.components[k])).map(([k, label, color]) => ({
      label,
      backgroundColor: color,
      data: rec.options.map((o) => o.components[k] || 0),
    })),
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Recommendation</h1>
          {project && <p className="text-slate-500">{project.name} · {project.category}</p>}
        </div>
        <div className="flex gap-3">
          <Link to={`/projects/${projectId}/requirements`} className="rounded-lg border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50">
            Edit requirements
          </Link>
          <button onClick={generate} disabled={busy} className="rounded-lg bg-indigo-600 text-white px-4 py-2 hover:bg-indigo-500 disabled:opacity-60">
            {busy ? 'Working...' : rec ? 'Regenerate' : 'Generate recommendation'}
          </button>
        </div>
      </div>

      <ProjectTabs projectId={projectId} />
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!rec && !error && (
        <p className="text-slate-500">No recommendation yet. Click "Generate recommendation".</p>
      )}

      {rec && (
        <>
          <div className="bg-white rounded-xl shadow p-6 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-800">ML prediction</h2>
              <span className="text-xs rounded-full bg-amber-100 text-amber-800 px-2 py-0.5">Trained on synthetic data</span>
              <span className="text-xs rounded-full bg-slate-100 text-slate-700 px-2 py-0.5">Prices: {rec.price_source}</span>
            </div>
            <p className="text-slate-700">
              Predicted need: {rec.ml.predicted_vcpu} vCPU, {rec.ml.predicted_ram_gb} GB RAM, family "{rec.ml.predicted_family}".
              Final sizing used: {rec.sizing.vcpu} vCPU, {rec.sizing.ram_gb} GB RAM ({rec.sizing.basis.toLowerCase()}).
            </p>
            <p className="text-sm font-medium text-indigo-700">{rec.budget_verdict}</p>
          </div>

          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-3">Monthly cost by option (USD)</h2>
            <Bar
              data={chartData}
              options={{
                responsive: true,
                scales: { x: { stacked: true }, y: { stacked: true, title: { display: true, text: 'USD per month' } } },
              }}
            />
            <p className="text-sm text-slate-500 mt-2">Your budget: {money(rec.budget_usd)} per month. Region: {rec.region}.</p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {rec.options.map((o) => (
              <div key={o.key} className="bg-white rounded-xl shadow p-5 space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-800">{o.label}</h3>
                  <span className={'text-xs rounded-full px-2 py-0.5 ' + (o.within_budget ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800')}>
                    {o.within_budget ? 'In budget' : 'Over budget'}
                  </span>
                </div>
                <p className="text-2xl font-bold text-slate-900">{money(o.monthly_usd)}<span className="text-sm font-normal text-slate-500"> / month</span></p>
                <p className="text-sm text-slate-700">{o.compute}</p>
                {o.vcpu_total && <p className="text-sm text-slate-500">{o.vcpu_total} vCPU, {o.ram_total} GB RAM in total</p>}
                <p className="text-sm text-slate-500">{o.summary}</p>
                <p className="text-sm text-slate-600">Storage: {o.storage.service}</p>
                {o.savings.savings_plan_total != null && (
                  <p className="text-xs text-slate-500">With a 1-year Savings Plan (illustrative): {money(o.savings.savings_plan_total)}</p>
                )}
                {o.savings.spot_total != null && (
                  <p className="text-xs text-slate-500">With Spot, for interruptible work (illustrative): {money(o.savings.spot_total)}</p>
                )}
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl shadow p-6 space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">Database</h2>
              <p className="text-slate-700">{rec.database.service}</p>
              {rec.database.note && <p className="text-sm text-slate-500">{rec.database.note}</p>}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800">Networking</h2>
              <ul className="list-disc ml-5 text-slate-700 text-sm space-y-1">{rec.networking.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800">Monitoring</h2>
              <ul className="list-disc ml-5 text-slate-700 text-sm space-y-1">{rec.monitoring.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-2">Assumptions</h2>
            <ul className="list-disc ml-5 text-slate-600 text-sm space-y-1">{rec.assumptions.map((x) => <li key={x}>{x}</li>)}</ul>
          </div>
        </>
      )}
    </div>
  )
}

