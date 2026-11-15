import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../api'
import { useAuth } from '../context/AuthContext.jsx'

const pct = (n) => (n == null ? '-' : (n * 100).toFixed(1) + '%')

function Card({ title, children }) {
  return (
    <div className="bg-white rounded-xl shadow p-6 space-y-2 text-sm">
      <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
      {children}
    </div>
  )
}

export default function Settings() {
  const { user } = useAuth()
  const [s, setS] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/settings').then((r) => setS(r.data)).catch((e) => setError(errorMessage(e)))
  }, [])

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-800">Settings</h1>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!s && !error && <p className="text-slate-500">Loading...</p>}

      <Card title="Account">
        <p>{user?.name} · {user?.email}</p>
        <Link to="/profile" className="text-indigo-600 underline">Edit profile or change password</Link>
      </Card>

      {s && (
        <>
          <Card title="AWS connection">
            {s.aws.connected
              ? <p className="text-green-700">Connected as {s.aws.identity} (profile {s.aws.profile}, account ending {s.aws.account_suffix}).</p>
              : <p className="text-amber-700">{s.aws.reason}</p>}
            <p className="text-slate-500">Default region: {s.default_region}</p>
          </Card>

          <Card title="Safety controls (read-only)">
            <p>Deployment: <b className={s.deploy_enabled ? 'text-red-700' : 'text-green-700'}>{s.deploy_enabled ? 'ENABLED' : 'switched off'}</b></p>
            <p>Cost cap per deployment: <b>${Number(s.cost_cap).toFixed(2)}</b> per month</p>
            <p>Price source: <b>{s.pricing_mode === 'live' ? 'live (AWS Price List API)' : 'reference table'}</b></p>
            <p className="text-slate-500">These are set in backend/.env and need a server restart. They cannot be changed from the browser on purpose.</p>
          </Card>

          <Card title="Machine learning models">
            {s.model.available ? (
              <>
                <p className="rounded-lg bg-amber-50 border border-amber-200 p-2 text-amber-900">
                  Data source: <b>{s.model.data_source}</b>. {s.model.warning}
                </p>
                <p>Train rows {s.model.train_rows}, test rows {s.model.test_rows}</p>
                <p>Random Forest R2: vCPU {s.model.rf_r2_vcpu?.toFixed(3)}, RAM {s.model.rf_r2_ram?.toFixed(3)}</p>
                <p>Linear Regression R2: vCPU {s.model.lr_r2_vcpu?.toFixed(3)}, RAM {s.model.lr_r2_ram?.toFixed(3)}</p>
                <p>Instance family classifier: {s.model.classifier}, accuracy {pct(s.model.classifier_accuracy)}</p>
              </>
            ) : <p className="text-red-600">Model report not found. Run ml/train_models.py.</p>}
          </Card>

          <Card title="Your data">
            <p>{s.counts.projects} projects · {s.counts.recommendations} recommendations · {s.counts.deployments} deployment runs</p>
          </Card>
        </>
      )}
    </div>
  )
}
