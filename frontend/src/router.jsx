import { Navigate, Route, Routes } from 'react-router-dom'
import App from './pages/App.jsx'
import Verify from './pages/Verify.jsx'
import AddData from './pages/AddData.jsx'
import Spec from './pages/Spec.jsx'

// /app: Mei's app   /data: add your data (demo)   /v/:id: landlord verify page   /spec: standard spec
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/app" element={<App />} />
      <Route path="/data" element={<AddData />} />
      <Route path="/v/:id" element={<Verify />} />
      <Route path="/spec" element={<Spec />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  )
}
