import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api, { errorMessage } from '../api'
import ProjectTabs from '../components/ProjectTabs.jsx'

const money = (n) => (n == null ? '-' : '$' + Number(n).toFixed(2))
const STATUS_STYLE = {
  valid: 'text-green-700',
  invalid: 'text-red-700',
  error: 'text-red-700',
  skipped: 'text-amber-700',
}

export default function Template() {
  const { projectId } = useParams()
  const [options, setOptions] = useState([])
  const [optionKey, setOptionKey] = useState('')
  const [data, setData] = useState(null)
  const [result, setResult] = useState(null)
  const [aws, setAws] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const [r, s] = await Promise.all([
          api.get(`/projects/${projectId}/recommendation`),
          api.get('/aws/status'),
        ])
        const opts = r.data.recommendation?.options || []
        setOptions(opts)
        if (opts.length) setOptionKey(opts[0].key)
        setAws(s.data)
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [projectId])

  useEffect(() => {
    if (!optionKey) return
    setResult(null)
    setData(null)
    api
      .get(`/projects/${projectId}/template`, { params: { option: optionKey } })
      .then((res) => { setData(res.data); setError('') })
      .catch((err) => setError(errorMessage(err)))
  }, [projectId, optionKey])

  const validate = async () => {
    setBusy(true)
    setError('')
    try {
      const res = await api.post(`/projects/${projectId}/template/validate`, { option_key: optionKey })
      setResult(res.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const download = () => {
    const blob = new Blob([data.template], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${projectId}-${optionKey}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) return <p className="text-slate-500">Loading...</p>

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-800">CloudFormation template</h1>
      <ProjectTabs projectId={projectId} />
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!options.length && !error && <p className="text-slate-500">Generate the recommendation first.</p>}

      {aws && (
        <div className={'rounded-xl border p-3 text-sm ' + (aws.connected ? 'bg-green-50 border-green-200 text-green-900' : 'bg-amber-50 border-amber-200 text-amber-900')}>
          {aws.connected
            ? `AWS connected as ${aws.identity} (account ending ${aws.account_suffix}, profile ${aws.profile}). Validation only checks syntax and creates nothing.`
            : aws.reason}
        </div>
      )}

      {options.length > 0 && (
        <div className="bg-white rounded-xl shadow p-6 space-y-4">
          <div className="flex flex-wrap gap-2">
            {options.map((o) => (
              <button
                key={o.key}
                onClick={() => setOptionKey(o.key)}
                className={'px-3 py-1 rounded-lg text-sm ' + (o.key === optionKey ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600')}
              >
                {o.label}
              </button>
            ))}
          </div>

          {data && (
            <>
              <p className="text-sm text-slate-600">
                Region {data.region} · estimated {money(data.monthly_usd)} per month · {data.resources.length} resources · {data.size_bytes} bytes
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead><tr className="border-b"><th className="py-1 pr-4">Logical ID</th><th className="py-1">AWS resource type</th></tr></thead>
                  <tbody>
                    {data.resources.map((r) => (
                      <tr key={r.id} className="border-b last:border-0">
                        <td className="py-1 pr-4 text-slate-800">{r.id}</td>
                        <td className="py-1 text-slate-500">{r.type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex gap-3">
                <button onClick={validate} disabled={busy} className="rounded-lg bg-indigo-600 text-white px-4 py-2 hover:bg-indigo-500 disabled:opacity-60">
                  {busy ? 'Validating...' : 'Validate template'}
                </button>
                <button onClick={download} className="rounded-lg border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50">
                  Download JSON
                </button>
              </div>
              <details className="text-sm text-slate-600">
                <summary className="cursor-pointer">Show template JSON</summary>
                <pre className="mt-2 bg-slate-50 p-3 rounded overflow-auto max-h-96">{data.template}</pre>
              </details>
            </>
          )}
        </div>
      )}

      {result && (
        <div className="bg-white rounded-xl shadow p-6 space-y-2 text-sm">
          <h2 className="text-lg font-semibold text-slate-800">Validation result</h2>
          <p>Local checks: <b className={result.local.ok ? 'text-green-700' : 'text-red-700'}>{result.local.ok ? 'passed' : 'failed'}</b></p>
          {result.local.issues.map((i) => <p key={i} className="text-red-600">- {i}</p>)}
          <p>AWS CloudFormation: <b className={STATUS_STYLE[result.aws.status]}>{result.aws.status}</b> - {result.aws.message}</p>
          {result.aws.capabilities?.length > 0 && (
            <p className="text-slate-600">
              Deploying will need permission: {result.aws.capabilities.join(', ')} (it creates IAM roles). {result.aws.capabilities_reason}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
