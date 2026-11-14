import { useState } from 'react'
import api, { errorMessage } from '../api'
import { useAuth } from '../context/AuthContext.jsx'
import Field from '../components/Field.jsx'

export default function Profile() {
  const { user, setUser } = useAuth()
  const [name, setName] = useState(user.name)
  const [organization, setOrganization] = useState(user.organization || '')
  const [profileMsg, setProfileMsg] = useState('')
  const [profileErr, setProfileErr] = useState('')

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [pwMsg, setPwMsg] = useState('')
  const [pwErr, setPwErr] = useState('')

  const saveProfile = async (e) => {
    e.preventDefault()
    setProfileMsg('')
    setProfileErr('')
    try {
      const res = await api.put('/auth/me', { name, organization })
      setUser(res.data.user)
      setProfileMsg('Profile saved.')
    } catch (err) {
      setProfileErr(errorMessage(err))
    }
  }

  const changePassword = async (e) => {
    e.preventDefault()
    setPwMsg('')
    setPwErr('')
    try {
      await api.post('/auth/change-password', { current_password: current, new_password: next })
      setPwMsg('Password changed.')
      setCurrent('')
      setNext('')
    } catch (err) {
      setPwErr(errorMessage(err))
    }
  }

  return (
    <div className="space-y-6 max-w-lg">
      <h1 className="text-2xl font-bold text-slate-800">Profile</h1>

      <form onSubmit={saveProfile} className="bg-white rounded-xl shadow p-6 space-y-4">
        <Field label="Email" value={user.email} disabled readOnly />
        <Field label="Full name" value={name} onChange={(e) => setName(e.target.value)} required />
        <Field label="Organization" value={organization} onChange={(e) => setOrganization(e.target.value)} />
        {profileErr && <p className="text-red-600 text-sm">{profileErr}</p>}
        {profileMsg && <p className="text-green-600 text-sm">{profileMsg}</p>}
        <button className="rounded-lg bg-indigo-600 text-white px-4 py-2 hover:bg-indigo-500">Save profile</button>
      </form>

      <form onSubmit={changePassword} className="bg-white rounded-xl shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-800">Change password</h2>
        <Field label="Current password" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
        <Field label="New password" type="password" value={next} onChange={(e) => setNext(e.target.value)} required />
        {pwErr && <p className="text-red-600 text-sm">{pwErr}</p>}
        {pwMsg && <p className="text-green-600 text-sm">{pwMsg}</p>}
        <button className="rounded-lg bg-slate-800 text-white px-4 py-2 hover:bg-slate-700">Change password</button>
      </form>
    </div>
  )
}
