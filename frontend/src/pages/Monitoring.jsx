import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Line } from 'react-chartjs-2'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend } from 'chart.js'
import api, { errorMessage } from '../api'
import ProjectTabs from '../components/ProjectTabs.jsx'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend)

const COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']
const STATE = { OK: 'bg-green-100 text-green-800', ALARM: 'bg-red-100 text-red-800', INSUFFICIENT_DATA: 'bg-slate-100 text-slate-700' }

function toChart(chart) {
  const stamps = [...new Set(chart.series.flatMap((s) => s.timestamps))].sort()
  return {
    labels: stamps.map((t) => new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })),
    datasets: chart.series.map((s, i) => {
      const byTime = Object.fromEntries(s.timestamps.map((t, j) => [t, s.values[j]]))
      return {
        label: s.label,
        data: stamps.map((t) => (t in byTime ? byTime[t] : null)),
        borderColor: COLORS[i % COLORS.length],
        backgroundColor: COLORS[i % COLORS.length],
        pointRadius: 1,
        spanGaps: true,
      }
    }),
  }
}

export default function Monitoring() {
  const { projectId } = useParams()
  const [hours, setHours] = useState(3)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get(`/projects/${projectId}/monitoring`, { params: { hours } })
      setData(res.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [projectId, hours])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-800">Monitoring</h1>
      <ProjectTabs projectId={projectId} />
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {loading && <p className="text-slate-500">Loading from CloudWatch...</p>}

      {data && !data.available && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{data.reason}</div>
      )}

      {data?.available && (
        <>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="text-slate-600">Stack {data.stack_name} in {data.region}</span>
            <select value={hours} onChange={(e) => setHours(Number(e.target.value))} className="rounded-lg border border-slate-300 px-2 py-1 bg-white">
              <option value={1}>Last hour</option>
              <option value={3}>Last 3 hours</option>
              <option value={6}>Last 6 hours</option>
              <option value={24}>Last 24 hours</option>
            </select>
            <button onClick={load} className="rounded-lg bg-indigo-600 text-white px-3 py-1 hover:bg-indigo-500">Refresh</button>
          </div>

          {data.notes.map((n) => (
            <div key={n} className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{n}</div>
          ))}

          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-2">Alarms</h2>
            {data.alarms.length === 0 && <p className="text-sm text-slate-500">No alarms found in this stack.</p>}
            <ul className="space-y-2 text-sm">
              {data.alarms.map((a) => (
                <li key={a.name}>
                  <span className={'rounded-full px-2 py-0.5 text-xs mr-2 ' + (STATE[a.state] || '')}>{a.state}</span>
                  <b>{a.description || a.name}</b>
                  <span className="block text-slate-500 text-xs">{a.reason}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {data.charts.map((c) => (
              <div key={c.key} className="bg-white rounded-xl shadow p-4">
                <h3 className="font-semibold text-slate-800">{c.title}</h3>
                <p className="text-xs text-slate-500 mb-2">Unit: {c.unit}, one point per {data.period_seconds / 60} minutes</p>
                <Line
                  data={toChart(c)}
                  options={{ responsive: true, plugins: { legend: { display: c.series.length > 1 } }, scales: { y: { beginAtZero: true } } }}
                />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
