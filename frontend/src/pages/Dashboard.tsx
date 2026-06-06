import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getSquad } from '../api/squad'
import { DemoBanner } from '../components/DemoBanner'

function KPI({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      style={{
        padding: '20px 24px',
        background: '#fff',
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        minWidth: 180,
      }}
    >
      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, color: '#111827' }}>{value}</div>
    </div>
  )
}

export function Dashboard() {
  const qc = useQueryClient()
  const { data: players = [], isLoading } = useQuery({
    queryKey: ['squad'],
    queryFn: getSquad,
  })

  if (isLoading) return <p>Caricamento…</p>

  const playerCount = players.length
  const avgForm =
    playerCount > 0
      ? (players.reduce((s, p) => s + p.form, 0) / playerCount).toFixed(1)
      : '—'
  const topScorer =
    playerCount > 0 ? [...players].sort((a, b) => b.scoring - a.scoring)[0] : null
  const injured = players.filter((p) => p.injury_days > 0).length

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>

      <DemoBanner onSeeded={() => qc.invalidateQueries({ queryKey: ['squad'] })} />

      {playerCount === 0 ? (
        <p style={{ color: '#6b7280' }}>
          Nessun dato. Vai in{' '}
          <Link to="/settings">Impostazioni</Link> per configurare CHPP, poi{' '}
          <Link to="/squad">sincronizza la rosa</Link>.
        </p>
      ) : (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <KPI label="Giocatori in rosa" value={playerCount} />
          <KPI label="Forma media" value={avgForm} />
          <KPI
            label="Miglior attaccante"
            value={
              topScorer
                ? `${topScorer.first_name} ${topScorer.last_name} (${topScorer.scoring})`
                : '—'
            }
          />
          <KPI label="Infortunati" value={injured} />
        </div>
      )}
    </div>
  )
}
