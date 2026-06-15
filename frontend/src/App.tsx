import { createBrowserRouter, RouterProvider, NavLink, Outlet } from 'react-router-dom'
import { PrePartita } from './pages/PrePartita'
import { Stagione } from './pages/Stagione'
import { Girone } from './pages/Girone'
import { Squad } from './pages/Squad'
import { Settings } from './pages/Settings'
import { PlayerDetail } from './pages/PlayerDetail'

function Layout() {
  const navStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
    padding: '8px 16px',
    textDecoration: 'none',
    color: isActive ? '#3b82f6' : '#374151',
    fontWeight: isActive ? 600 : 400,
    borderBottom: isActive ? '2px solid #3b82f6' : '2px solid transparent',
  })

  return (
    <div style={{ minHeight: '100vh', fontFamily: 'system-ui, sans-serif', background: '#f9fafb' }}>
      <nav style={{ display: 'flex', gap: 4, padding: '0 24px', borderBottom: '1px solid #e5e7eb', background: '#fff' }}>
        <NavLink to="/" end style={navStyle}>Pre-Partita</NavLink>
        <NavLink to="/stagione" style={navStyle}>Stagione</NavLink>
        <NavLink to="/girone" style={navStyle}>Girone</NavLink>
        <NavLink to="/rosa" style={navStyle}>Rosa</NavLink>
        <NavLink to="/impostazioni" style={navStyle}>Impostazioni</NavLink>
      </nav>
      <main style={{ padding: '24px' }}>
        <Outlet />
      </main>
    </div>
  )
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <PrePartita /> },
      { path: 'stagione', element: <Stagione /> },
      { path: 'girone', element: <Girone /> },
      { path: 'rosa', element: <Squad /> },
      { path: 'rosa/:id', element: <PlayerDetail /> },
      { path: 'impostazioni', element: <Settings /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
