import { useEffect, useRef, useState } from 'react'
import api, { errorMessage } from '../api'

const SUGGESTIONS = ['How much will it cost?', 'Why this instance?', 'Compare the options', 'How can I save money?', 'What is CloudWatch?']

export default function Chatbot() {
  const [projects, setProjects] = useState([])
  const [projectId, setProjectId] = useState('')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Hi! Select a project to ask about its cost and sizing, or ask me about an AWS service.', sources: [] },
  ])
  const [busy, setBusy] = useState(false)
  const bottom = useRef(null)

  useEffect(() => {
    api.get('/projects').then((res) => setProjects(res.data.projects)).catch(() => {})
  }, [])

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async (text) => {
    const message = (text ?? input).trim()
    if (!message || busy) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: message }])
    setBusy(true)
    try {
      const res = await api.post('/assistant', { message, project_id: projectId })
      setMessages((m) => [...m, { role: 'bot', text: res.data.answer, sources: res.data.sources }])
    } catch (err) {
      setMessages((m) => [...m, { role: 'bot', text: errorMessage(err), sources: [] }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-800">AI Cloud Assistant</h1>
      <p className="text-sm text-slate-500">Answers come from your saved recommendations and AWS documentation. It is rule-based, not a large language model.</p>
      <select value={projectId} onChange={(e) => setProjectId(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 bg-white">
        <option value="">No project (general AWS questions)</option>
        {projects.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.category})</option>)}
      </select>

      <div className="bg-white rounded-xl shadow p-4 h-96 overflow-y-auto space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
            <div className={'inline-block max-w-full rounded-lg px-3 py-2 text-sm whitespace-pre-wrap text-left ' + (m.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-800')}>
              {m.text}
            </div>
            {m.sources?.length > 0 && (
              <div className="mt-1 text-xs text-slate-500">
                Docs: {m.sources.map((s, j) => (
                  <a key={j} href={s.url} target="_blank" rel="noreferrer" className="text-indigo-600 underline mr-2">{s.title}</a>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottom} />
      </div>

      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button key={s} onClick={() => send(s)} className="text-xs rounded-full bg-white shadow px-3 py-1 text-slate-600 hover:bg-slate-50">{s}</button>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask a question..."
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
        />
        <button onClick={() => send()} disabled={busy} className="rounded-lg bg-indigo-600 text-white px-4 py-2 hover:bg-indigo-500 disabled:opacity-60">Send</button>
      </div>
    </div>
  )
}
