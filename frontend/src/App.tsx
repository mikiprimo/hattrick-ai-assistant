import { createBrowserRouter, RouterProvider, NavLink, Outlet } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Squad } from './pages/Squad'
import { Settings } from './pages/Settings'
import { PlayerDetail } from './pages/PlayerDetail'
import { Training } from './pages/Training'
import { Matches } from './pages/Matches'
import { PrePartita } from './pages/PrePartita'

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
      <nav
        style={{
          display: 'flex',
          gap: 4,
          padding: '0 24px',
          borderBottom: '1px solid #e5e7eb',
          background: '#fff',
        }}
      >
        <NavLink to="/" end style={navStyle}>Dashboard</NavLink>
        <NavLink to="/squad" style={navStyle}>Rosa</NavLink>
        <NavLink to="/training" style={navStyle}>Allenamento</NavLink>
        <NavLink to="/matches" style={navStyle}>Partite</NavLink>
        <NavLink to="/pre-partita" style={navStyle}>Pre-Partita</NavLink>
        <NavLink to="/settings" style={navStyle}>Impostazioni</NavLink>
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
      { index: true, element: <Dashboard /> },
      { path: 'squad', element: <Squad /> },
      { path: 'players/:id', element: <PlayerDetail /> },
      { path: 'training', element: <Training /> },
      { path: 'matches', element: <Matches /> },
      { path: 'pre-partita', element: <PrePartita /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
