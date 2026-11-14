import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import mermaid from 'mermaid'
import api, { errorMessage } from '../api'
import ProjectTabs from '../components/ProjectTabs.jsx'

mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' })

export default function Architecture() {
  const { projectId } = useParams()
  const [diagrams, setDiagrams] = useState([])
  const [selected, setSelected] = useState('')
  const [svg, setSvg] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get(`/projects/${projectId}/architecture`)
      .then((res) => {
        setDiagrams(res.data.diagrams)
        setSelected(res.data.diagrams[0]?.key || '')
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [projectId])

  const current = diagrams.find((d) => d.key === selected)

  useEffect(() => {
    if (!current) return
    let cancelled = false
    mermaid
      .render('diagram' + Date.now(), current.mermaid)
      .then((out) => { if (!cancelled) { setSvg(out.svg); setError('') } })
      .catch(() => { if (!cancelled) setError('Could not draw the diagram.') })
    return () => { cancelled = true }
  }, [current])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-800">Architecture</h1>
      <ProjectTabs projectId={projectId} />
      {loading && <p className="text-slate-500">Loading...</p>}
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {diagrams.length > 0 && (
        <div className="bg-white rounded-xl shadow p-6 space-y-4">
          <div className="flex flex-wrap gap-2">
            {diagrams.map((d) => (
              <button
                key={d.key}
                onClick={() => setSelected(d.key)}
                className={'px-3 py-1 rounded-lg text-sm ' + (d.key === selected ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600')}
              >
                {d.label}
              </button>
            ))}
          </div>
          <div className="overflow-x-auto" dangerouslySetInnerHTML={{ __html: svg }} />
          <details className="text-sm text-slate-600">
            <summary className="cursor-pointer">Show Mermaid source</summary>
            <pre className="mt-2 bg-slate-50 p-3 rounded overflow-x-auto">{current?.mermaid}</pre>
          </details>
        </div>
      )}
    </div>
  )
}
