import { useEffect, useState } from 'react'
import axios from 'axios'

export default function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    axios
      .get('/api/health')
      .then((res) => setHealth(res.data))
      .catch((err) => {
        if (err.response) {
          setError(
            'Backend is running, but: database ' +
              (err.response.data.database || 'error') +
              ' (' + (err.response.data.detail || err.response.status) + ')'
          )
        } else {
          setError('Backend not reachable. Is the server running on port 5000?')
        }
      })
  }, [])

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-6">
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full">
        <h1 className="text-2xl font-bold text-slate-800">
          Cloud Resource Recommender
        </h1>
        <p className="text-slate-500 mt-1">Step 1: environment check</p>

        <div className="mt-6 space-y-2">
          {error && <p className="text-red-600">{error}</p>}
          {health && (
            <>
              <p>API status: <b className="text-green-600">{health.status}</b></p>
              <p>Database: <b className="text-green-600">{health.database}</b></p>
            </>
          )}
          {!health && !error && <p className="text-slate-400">Checking...</p>}
        </div>
      </div>
    </div>
  )
}
