import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import AppRoutes from './router.jsx'
import SiteNav from './components/SiteNav.jsx'
import './styles/index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <SiteNav />
      <AppRoutes />
    </BrowserRouter>
  </StrictMode>,
)
