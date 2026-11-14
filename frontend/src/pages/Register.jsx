import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { errorMessage } from '../api'
import Field from '../components/Field.jsx'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      await register(name, email, password)
      navigate('/')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-6">
      <form onSubmit={submit} className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full space-y-4">
        <h1 className="text-2xl font-bold text-slate-800">Create account</h1>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <Field label="Full name" value={name} onChange={(e) => setName(e.target.value)} required />
        <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Field label="Password (8+ characters, letters and numbers)" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <Field label="Confirm password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
        <button disabled={busy} className="w-full rounded-lg bg-indigo-600 text-white py-2 hover:bg-indigo-500 disabled:opacity-60">
          {busy ? 'Creating...' : 'Register'}
        </button>
        <p className="text-sm text-slate-500">
          Already registered? <Link to="/login" className="text-indigo-600 underline">Log in</Link>
        </p>
      </form>
    </div>
  )
}
