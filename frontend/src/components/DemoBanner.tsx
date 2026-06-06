import { useState } from 'react'
import { apiFetch } from '../api/client'

interface Props {
  onSeeded: () => void
}

export function DemoBanner({ onSeeded }: Props) {
  const [loading, setLoading] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [seeded, setSeeded] = useState(false)

  async function handleSeed() {
    setLoading(true)
    await apiFetch('/api/demo/seed', { method: 'POST' })
    setSeeded(true)
    setLoading(false)
    onSeeded()
  }

  async function handleClear() {
    setClearing(true)
    await apiFetch('/api/demo/seed', { method: 'DELETE' })
    setSeeded(false)
    setClearing(false)
    onSeeded()
  }

  return (
    <div
      style={{
        padding: '14px 18px',
        background: '#eff6ff',
        border: '1px solid #bfdbfe',
        borderRadius: 8,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
        flexWrap: 'wrap',
        marginBottom: 20,
      }}
    >
      <div>
        <span style={{ fontWeight: 600, color: '#1d4ed8', fontSize: 14 }}>Modalità demo</span>
        <span style={{ color: '#3b82f6', fontSize: 13, marginLeft: 8 }}>
          Carica 18 giocatori fittizi per esplorare la UI
        </span>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={handleSeed}
          disabled={loading}
          style={{
            padding: '6px 14px',
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: 13,
          }}
        >
          {loading ? 'Caricamento…' : 'Carica dati demo'}
        </button>
        {seeded && (
          <button
            onClick={handleClear}
            disabled={clearing}
            style={{
              padding: '6px 14px',
              background: 'transparent',
              color: '#6b7280',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              cursor: clearing ? 'not-allowed' : 'pointer',
              fontSize: 13,
            }}
          >
            {clearing ? '…' : 'Rimuovi'}
          </button>
        )}
      </div>
    </div>
  )
}
