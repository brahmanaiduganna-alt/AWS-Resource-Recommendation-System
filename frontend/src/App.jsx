import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Layout from './components/Layout.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Profile from './pages/Profile.jsx'
import Categories from './pages/Categories.jsx'
import Requirements from './pages/Requirements.jsx'
import Recommendation from './pages/Recommendation.jsx'
import Architecture from './pages/Architecture.jsx'
import Comparison from './pages/Comparison.jsx'
import Template from './pages/Template.jsx'
import Approval from './pages/Approval.jsx'
import Deployment from './pages/Deployment.jsx'
import DeploymentHistory from './pages/DeploymentHistory.jsx'
import Chatbot from './pages/Chatbot.jsx'
import Monitoring from './pages/Monitoring.jsx'
import Settings from './pages/Settings.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/categories" element={<Categories />} />
        <Route path="/requirements" element={<Requirements />} />
        <Route path="/projects/:projectId/requirements" element={<Requirements />} />
        <Route path="/projects/:projectId/recommendation" element={<Recommendation />} />
        <Route path="/projects/:projectId/architecture" element={<Architecture />} />
        <Route path="/projects/:projectId/comparison" element={<Comparison />} />
        <Route path="/projects/:projectId/template" element={<Template />} />
        <Route path="/projects/:projectId/approval" element={<Approval />} />
        <Route path="/projects/:projectId/deploy" element={<Deployment />} />
        <Route path="/projects/:projectId/monitoring" element={<Monitoring />} />
        <Route path="/deployments" element={<DeploymentHistory />} />
        <Route path="/assistant" element={<Chatbot />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
