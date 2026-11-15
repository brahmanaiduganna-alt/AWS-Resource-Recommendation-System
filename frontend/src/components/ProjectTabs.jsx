import { NavLink } from 'react-router-dom'

export default function ProjectTabs({ projectId }) {
  const cls = ({ isActive }) =>
    'px-3 py-1 rounded-lg text-sm ' +
    (isActive ? 'bg-indigo-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50 shadow')
  const base = `/projects/${projectId}`
  return (
    <div className="flex flex-wrap gap-2">
      <NavLink to={`${base}/recommendation`} className={cls}>Recommendation</NavLink>
      <NavLink to={`${base}/architecture`} className={cls}>Architecture</NavLink>
      <NavLink to={`${base}/comparison`} className={cls}>Comparison</NavLink>
      <NavLink to={`${base}/template`} className={cls}>Template</NavLink>
      <NavLink to={`${base}/approval`} className={cls}>Approval</NavLink>
      <NavLink to={`${base}/deploy`} className={cls}>Deploy</NavLink>
      <NavLink to={`${base}/monitoring`} className={cls}>Monitor</NavLink>
    </div>
  )
}
