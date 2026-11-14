import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../api'

export default function Categories() {
  const [categories, setCategories] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get('/meta')
      .then((res) => setCategories(res.data.categories))
      .catch((err) => setError(errorMessage(err)))
  }, [])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Choose a project category</h1>
        <p className="text-slate-500">Pick the type of project you want cloud resources for.</p>
      </div>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map((c) => (
          <Link
            key={c.name}
            to={`/requirements?category=${encodeURIComponent(c.name)}`}
            className="bg-white rounded-xl shadow p-5 hover:shadow-md hover:ring-2 hover:ring-indigo-300 transition"
          >
            <h2 className="text-lg font-semibold text-slate-800">{c.name}</h2>
            <p className="text-sm text-slate-500 mt-2">{c.description}</p>
            <p className="text-sm text-indigo-600 mt-3">Start project</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
