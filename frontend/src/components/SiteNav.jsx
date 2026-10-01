import { NavLink, useLocation } from 'react-router-dom'

// Worker-side navigation. Never shown on the landlord's verify page (/v/:id).
export default function SiteNav() {
  const { pathname } = useLocation()
  if (pathname.startsWith('/v/')) return null
  return (
    <nav className="site-nav" aria-label="Main">
      <ul>
        <li>
          <NavLink to="/app">My income</NavLink>
        </li>
        <li>
          <NavLink to="/data">Add your data</NavLink>
        </li>
        <li>
          <NavLink to="/spec">The standard</NavLink>
        </li>
      </ul>
    </nav>
  )
}
