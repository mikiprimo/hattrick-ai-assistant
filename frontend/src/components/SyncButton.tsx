import { useState } from 'react'
import { triggerSync } from '../api/sync'

interface Props {
  entity: string
  onSynced?: () => void
}

export function SyncButton({ entity, onSynced }: Props) {
  const [loading, setLoading] = useState(false)
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSync() {
    setLoading(true)
    setError(null)
    try {
      const result = await triggerSync(entity)
      setSyncedAt(result.synced_at)
      onSynced?.()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Errore')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <button
        onClick={handleSync}
        disabled={loading}
        style={{
          padding: '6px 14px',
          background: loading ? '#93c5fd' : '#3b82f6',
          color: '#fff',
          border: 'none',
          borderRadius: 6,
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: 13,
        }}
      >
        {loading ? 'Sincronizzazione…' : 'Sincronizza'}
      </button>
      {syncedAt && (
        <span style={{ fontSize: 12, color: '#6b7280' }}>
          Aggiornato: {new Date(syncedAt).toLocaleString('it-IT')}
        </span>
      )}
      {error && <span style={{ fontSize: 12, color: '#ef4444' }}>{error}</span>}
    </div>
  )
}
